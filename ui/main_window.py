from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QListWidget,QListWidgetItem,QFileDialog,QComboBox,QProgressBar,
    QMessageBox,QFrame,QSpinBox,QCheckBox,QAbstractItemView,QTabWidget,
    QLineEdit,QTextEdit,QFormLayout,QGroupBox
)
from core.engine import ffmpeg_path, probe_media, run_ffmpeg, unique_path
from converters.media import AUDIO_FORMATS,VIDEO_FORMATS,convert_audio,convert_video,extract_audio,to_gif
from converters.images import IMAGE_FORMATS,convert_image,images_to_gif
from converters.archive import extract_archive
from ui.styles import STYLE

IMAGE_INPUTS={".png",".jpg",".jpeg",".webp",".avif",".bmp",".tif",".tiff",".gif",".ico"}
VIDEO_INPUTS={".mp4",".mkv",".webm",".mov",".avi",".wmv",".m4v",".ts",".mts",".m2ts"}
AUDIO_INPUTS={".mp3",".wav",".flac",".ogg",".oga",".opus",".aac",".m4a",".aiff",".aif",".wma"}
ARCHIVE_INPUTS={".zip",".tar",".gz",".bz2",".xz"}

class Worker(QObject):
    progress=Signal(int); message=Signal(str); error=Signal(str); done=Signal(); cancelled=Signal()
    def __init__(self,fn): super().__init__(); self.fn=fn; self.cancel_requested=False
    def cancel(self): self.cancel_requested=True
    def run(self):
        try:
            self.fn(self)
            (self.cancelled if self.cancel_requested else self.done).emit()
        except InterruptedError: self.cancelled.emit()
        except Exception as e: self.error.emit(str(e)); self.done.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Woods Media Converter"); self.resize(1120,780)
        self.setAcceptDrops(True); self.files=[]; self.thread=None; self.worker=None
        self.build_ui(); self.setStyleSheet(STYLE); self.update_engine()

    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root)
        main.setContentsMargins(28,24,28,24); main.setSpacing(16)
        header=QHBoxLayout(); titles=QVBoxLayout()
        title=QLabel("Woods Media Converter"); title.setObjectName("title")
        sub=QLabel("Local conversion. No uploads. No cloud. No nonsense."); sub.setObjectName("subtitle")
        titles.addWidget(title); titles.addWidget(sub); header.addLayout(titles); header.addStretch()
        self.engine=QLabel("● Local engine"); self.engine.setObjectName("engine"); header.addWidget(self.engine)
        main.addLayout(header)
        self.tabs=QTabWidget(); main.addWidget(self.tabs,1)
        self.converter_tab=QWidget(); self.build_converter_tab(); self.tabs.addTab(self.converter_tab,"Convert")
        self.metadata_tab=QWidget(); self.build_metadata_tab(); self.tabs.addTab(self.metadata_tab,"Metadata & Scrub")
        self.lab_tab=QWidget(); self.build_lab_tab(); self.tabs.addTab(self.lab_tab,"File Lab")

    def build_converter_tab(self):
        layout=QVBoxLayout(self.converter_tab); layout.setContentsMargins(0,12,0,0)
        drop=QFrame(); drop.setObjectName("dropArea"); drop.setMinimumHeight(110); dl=QVBoxLayout(drop); dl.setAlignment(Qt.AlignCenter)
        t=QLabel("Drop files here"); t.setObjectName("dropTitle"); t.setAlignment(Qt.AlignCenter)
        h=QLabel("Audio • Video • Images • Archives"); h.setObjectName("dropHint"); h.setAlignment(Qt.AlignCenter)
        dl.addWidget(t); dl.addWidget(h); layout.addWidget(drop)
        bar=QHBoxLayout()
        for text,slot in [("+ Add Files",self.add_files),("Add Folder",self.add_folder),("Remove Selected",self.remove_selected),("Clear",self.clear_files)]:
            b=QPushButton(text); b.clicked.connect(slot); bar.addWidget(b)
            if text=="+ Add Files": self.add_btn=b
            elif text=="Add Folder": self.add_folder_btn=b
            elif text=="Remove Selected": self.remove_btn=b
            else: self.clear_btn=b
        bar.addStretch(); layout.addLayout(bar)
        self.file_list=QListWidget(); self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection); layout.addWidget(self.file_list,1)
        card=QFrame(); card.setObjectName("card"); form=QHBoxLayout(card)
        a=QVBoxLayout(); a.addWidget(QLabel("Operation")); self.operation=QComboBox()
        self.operation.addItems(["Auto convert","Audio convert","Extract audio","Video convert","Video → GIF","Image convert","Images → GIF","Extract archive"])
        self.operation.currentTextChanged.connect(self.refresh_formats); a.addWidget(self.operation); form.addLayout(a)
        b=QVBoxLayout(); b.addWidget(QLabel("Format")); self.format_combo=QComboBox(); b.addWidget(self.format_combo); form.addLayout(b)
        c=QVBoxLayout(); c.addWidget(QLabel("Quality / Bitrate")); self.quality=QSpinBox(); self.quality.setRange(32,512); self.quality.setValue(192); self.quality.setSuffix(" kbps"); c.addWidget(self.quality); form.addLayout(c)
        d=QVBoxLayout(); d.addWidget(QLabel("Output")); row=QHBoxLayout(); self.output=QLabel(str(Path.home()/"Music")); self.output.setObjectName("muted")
        self.browse=QPushButton("Browse"); self.browse.clicked.connect(self.choose_output); row.addWidget(self.output,1); row.addWidget(self.browse); d.addLayout(row); form.addLayout(d,2)
        self.no_overwrite=QCheckBox("Don't overwrite"); self.no_overwrite.setChecked(True); form.addWidget(self.no_overwrite); layout.addWidget(card)
        status=QHBoxLayout(); self.status=QLabel("Ready"); self.status.setObjectName("muted"); status.addWidget(self.status); status.addStretch()
        self.progress=QProgressBar(); self.progress.setFixedWidth(280); status.addWidget(self.progress); layout.addLayout(status)
        buttons=QHBoxLayout(); self.cancel=QPushButton("Cancel"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.cancel_job)
        self.convert=QPushButton("Convert"); self.convert.setObjectName("primary"); self.convert.clicked.connect(self.start_conversion)
        buttons.addWidget(self.cancel); buttons.addStretch(); buttons.addWidget(self.convert); layout.addLayout(buttons)
        self.refresh_formats(self.operation.currentText())

    def build_metadata_tab(self):
        layout=QVBoxLayout(self.metadata_tab); layout.setContentsMargins(0,12,0,0)
        row=QHBoxLayout(); self.meta_file=QLineEdit(); self.meta_file.setPlaceholderText("Choose a media file...")
        b=QPushButton("Browse"); b.clicked.connect(self.choose_metadata_file); row.addWidget(self.meta_file,1); row.addWidget(b); layout.addLayout(row)
        form=QFormLayout(); self.meta_fields={}
        for key,label in [("title","Title"),("artist","Artist"),("album","Album"),("album_artist","Album Artist"),("genre","Genre"),("date","Year / Date"),("tracknumber","Track"),("comment","Comment")]:
            e=QLineEdit(); self.meta_fields[key]=e; form.addRow(label,e)
        group=QGroupBox("Common tags"); group.setLayout(form); layout.addWidget(group)
        buttons=QHBoxLayout()
        for text,slot in [("Read Metadata",self.read_metadata),("Write Metadata",self.write_metadata),("Scrub All Metadata",self.scrub_metadata)]:
            b=QPushButton(text); b.clicked.connect(slot); buttons.addWidget(b)
        buttons.addStretch(); layout.addLayout(buttons)
        self.meta_info=QTextEdit(); self.meta_info.setReadOnly(True); layout.addWidget(self.meta_info,1)

    def build_lab_tab(self):
        layout=QVBoxLayout(self.lab_tab); layout.setContentsMargins(0,12,0,0)
        layout.addWidget(QLabel("Make Your Own Header™"))
        info=QLabel("A deliberately simple binary container playground. Create a custom header, then append a payload."); info.setObjectName("muted"); layout.addWidget(info)
        form=QFormLayout(); self.magic=QLineEdit("WOODS"); self.version=QSpinBox(); self.version.setRange(0,65535); self.version.setValue(1)
        self.flags=QSpinBox(); self.flags.setRange(0,2147483647); self.header_size=QSpinBox(); self.header_size.setRange(16,4096); self.header_size.setValue(32)
        form.addRow("Magic",self.magic); form.addRow("Version",self.version); form.addRow("Flags",self.flags); form.addRow("Header size",self.header_size)
        box=QGroupBox("Header"); box.setLayout(form); layout.addWidget(box)
        row=QHBoxLayout(); self.lab_payload=QLineEdit(); self.lab_payload.setPlaceholderText("Optional payload file"); choose=QPushButton("Choose Payload"); choose.clicked.connect(self.choose_lab_payload)
        row.addWidget(self.lab_payload,1); row.addWidget(choose); layout.addLayout(row)
        make=QPushButton("CREATE THE ABOMINATION"); make.setObjectName("primary"); make.clicked.connect(self.create_custom_file); layout.addWidget(make); layout.addStretch()

    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,"Select Files",str(Path.home()),"All Files (*)"); self.add_paths([Path(x) for x in files])
    def add_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Select Folder",str(Path.home()))
        if folder: self.add_paths([p for p in Path(folder).rglob("*") if p.is_file()])
    def add_paths(self,paths):
        existing={str(Path(x).resolve()) for x in self.files}
        for p in paths:
            if p.is_file() and str(p.resolve()) not in existing:
                self.files.append(str(p)); item=QListWidgetItem(f"{p.name}   •   {self.kind(p)}   •   {self.size(p)}"); item.setToolTip(str(p)); self.file_list.addItem(item); existing.add(str(p.resolve()))
        self.status.setText(f"{len(self.files)} file(s) queued")
    @staticmethod
    def size(p):
        try:
            n=p.stat().st_size
            for u in ("B","KB","MB","GB"):
                if n<1024:return f"{n:.1f} {u}"
                n/=1024
            return f"{n:.1f} TB"
        except OSError:return "?"
    @staticmethod
    def kind(p):
        e=p.suffix.lower()
        if e in AUDIO_INPUTS:return "Audio"
        if e in VIDEO_INPUTS:return "Video"
        if e in IMAGE_INPUTS:return "Image"
        if e in ARCHIVE_INPUTS:return "Archive"
        return "File"
    def remove_selected(self):
        rows=sorted([self.file_list.row(x) for x in self.file_list.selectedItems()],reverse=True)
        for r in rows:self.file_list.takeItem(r); self.files.pop(r)
        self.status.setText(f"{len(self.files)} file(s) queued")
    def clear_files(self):
        self.files.clear(); self.file_list.clear(); self.progress.setValue(0); self.status.setText("Ready")
    def choose_output(self):
        f=QFileDialog.getExistingDirectory(self,"Output Folder",self.output.text())
        if f:self.output.setText(f)
    def refresh_formats(self,op):
        self.format_combo.clear()
        if op in ("Audio convert","Extract audio"): self.format_combo.addItems(AUDIO_FORMATS.keys())
        elif op=="Video convert": self.format_combo.addItems(VIDEO_FORMATS.keys())
        elif op=="Image convert": self.format_combo.addItems(IMAGE_FORMATS.keys())
        elif op=="Auto convert": self.format_combo.addItems(["MP4","MP3","PNG","WebP"])
        elif op in ("Video → GIF","Images → GIF"): self.format_combo.addItem("GIF")
        else:self.format_combo.addItem("Folder")

    def start_conversion(self):
        if not self.files:return QMessageBox.information(self,"Nothing to do","Add some files first.")
        if not ffmpeg_path() and any(self.kind(Path(x)) in ("Audio","Video") for x in self.files):
            return QMessageBox.critical(self,"FFmpeg unavailable","The bundled FFmpeg engine is unavailable.")
        out=Path(self.output.text()); out.mkdir(parents=True,exist_ok=True)
        op=self.operation.currentText(); fmt=self.format_combo.currentText(); bitrate=self.quality.value(); files=[Path(x) for x in self.files]
        def job(w):
            if op=="Images → GIF":
                r=images_to_gif(files,out); w.message.emit(f"Created {r.name}"); w.progress.emit(100); return
            total=len(files)
            for i,src in enumerate(files):
                if w.cancel_requested: raise InterruptedError()
                w.message.emit(f"Converting {src.name}")
                if op=="Extract archive": r=extract_archive(src,out)
                elif op=="Video → GIF": r=to_gif(src,out,cancel_check=lambda:w.cancel_requested)
                elif op=="Audio convert": r=convert_audio(src,out,fmt,bitrate,lambda:w.cancel_requested)
                elif op=="Extract audio": r=extract_audio(src,out,fmt,bitrate,lambda:w.cancel_requested)
                elif op=="Video convert": r=convert_video(src,out,fmt,cancel_check=lambda:w.cancel_requested)
                elif op=="Image convert": r=convert_image(src,out,fmt,quality=bitrate)
                elif src.suffix.lower() in VIDEO_INPUTS: r=convert_video(src,out,"MP4",cancel_check=lambda:w.cancel_requested)
                elif src.suffix.lower() in AUDIO_INPUTS: r=convert_audio(src,out,"MP3",bitrate,lambda:w.cancel_requested)
                elif src.suffix.lower() in IMAGE_INPUTS: r=convert_image(src,out,"PNG")
                else: raise ValueError(f"Cannot auto-convert {src.name}")
                w.message.emit(f"Created {Path(r).name}"); w.progress.emit(int((i+1)/total*100))
        self.set_busy(True); self.thread=QThread(); self.worker=Worker(job); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.progress.setValue); self.worker.message.connect(self.status.setText)
        self.worker.error.connect(self.on_error); self.worker.done.connect(self.on_done); self.worker.cancelled.connect(self.on_cancelled); self.thread.start()

    def set_busy(self,b):
        for x in (self.add_btn,self.add_folder_btn,self.remove_btn,self.clear_btn,self.browse,self.convert):x.setEnabled(not b)
        self.cancel.setEnabled(b)
    def cancel_job(self):
        if self.worker:self.worker.cancel(); self.status.setText("Cancelling...")
    def cleanup(self):
        if self.thread:self.thread.quit(); self.thread.wait()
        self.thread=None; self.worker=None; self.set_busy(False)
    def on_done(self):
        self.cleanup(); self.progress.setValue(100); self.status.setText("Finished"); QMessageBox.information(self,"Done","Conversion finished.")
    def on_cancelled(self):
        self.cleanup(); self.progress.setValue(0); self.status.setText("Cancelled")
    def on_error(self,msg):
        self.cleanup(); self.status.setText("Error"); QMessageBox.critical(self,"Conversion error",msg)

    def choose_metadata_file(self):
        f,_=QFileDialog.getOpenFileName(self,"Select Media File",str(Path.home()),"All Files (*)")
        if f:self.meta_file.setText(f); self.read_metadata()
    def read_metadata(self):
        p=self.meta_file.text().strip()
        if not p:return
        try:
            self.meta_info.setPlainText(probe_media(p)["raw"])
            try:
                from mutagen import File
                a=File(p,easy=True)
                if a:
                    for k,e in self.meta_fields.items():
                        vals=a.get(k); e.setText(str(vals[0]) if vals else "")
            except Exception:pass
        except Exception as e:QMessageBox.critical(self,"Metadata",str(e))
    def write_metadata(self):
        p=Path(self.meta_file.text().strip())
        if not p.exists():return QMessageBox.information(self,"Metadata","Choose a file first.")
        dst=unique_path(p.with_name(p.stem+" (tagged)"+p.suffix))
        args=["-y","-i",str(p),"-c","copy","-map_metadata","0"]
        for k,e in self.meta_fields.items():
            if e.text().strip():args += ["-metadata",f"{k}={e.text().strip()}"]
        args += [str(dst)]
        try:run_ffmpeg(args); QMessageBox.information(self,"Metadata",f"Saved:\n{dst}")
        except Exception as e:QMessageBox.critical(self,"Metadata",str(e))
    def scrub_metadata(self):
        p=Path(self.meta_file.text().strip())
        if not p.exists():return QMessageBox.information(self,"Scrub","Choose a file first.")
        dst=unique_path(p.with_name(p.stem+" (scrubbed)"+p.suffix))
        try:run_ffmpeg(["-y","-i",str(p),"-map_metadata","-1","-c","copy",str(dst)]); QMessageBox.information(self,"Scrubbed",f"Created:\n{dst}")
        except Exception as e:QMessageBox.critical(self,"Scrub",str(e))

    def choose_lab_payload(self):
        f,_=QFileDialog.getOpenFileName(self,"Payload",str(Path.home()),"All Files (*)")
        if f:self.lab_payload.setText(f)
    def create_custom_file(self):
        dst,_=QFileDialog.getSaveFileName(self,"Create Custom File",str(Path.home()/"abomination.woods"),"All Files (*)")
        if not dst:return
        try:
            n=self.header_size.value(); magic=self.magic.text().encode()[:8]; h=bytearray(n); h[:len(magic)]=magic
            h[8:10]=self.version.value().to_bytes(2,"little"); h[10:14]=self.flags.value().to_bytes(4,"little")
            payload=Path(self.lab_payload.text()).read_bytes() if self.lab_payload.text() else b""
            h[14:22]=len(payload).to_bytes(8,"little"); Path(dst).write_bytes(bytes(h)+payload)
            QMessageBox.information(self,"File Lab",f"Created:\n{dst}")
        except Exception as e:QMessageBox.critical(self,"File Lab",str(e))

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        self.add_paths([Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()])
    def update_engine(self):
        self.engine.setText("● Local FFmpeg engine ready" if ffmpeg_path() else "● FFmpeg engine unavailable")
    def closeEvent(self,event):
        if self.worker:self.worker.cancel()
        if self.thread:self.thread.quit(); self.thread.wait()
        event.accept()
