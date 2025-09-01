import imghdr
import os

from werkzeug.utils import secure_filename

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "pdf"}
MAX_SIZE_MB = 8


def validate_upload(file_storage) -> None:
    """
    Basit sunucu tarafı dosya doğrulama:
    - Güvenli dosya adı
    - Uzantı beyaz listesi
    - Boyut sınırı
    - Görsellerde sihirli bayrak kontrolü
    """
    filename = secure_filename(file_storage.filename or "")
    if "." not in filename:
        raise ValueError("Geçersiz dosya adı")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Desteklenmeyen dosya türü")
    # Boyut
    pos = file_storage.stream.tell()
    file_storage.stream.seek(0, os.SEEK_END)
    size_mb = file_storage.stream.tell() / (1024 * 1024)
    file_storage.stream.seek(pos)
    if size_mb > MAX_SIZE_MB:
        raise ValueError("Dosya boyutu limit aşıldı")
    # Görsel kontrolü
    if ext in {"png", "jpg", "jpeg", "webp"}:
        head = file_storage.read(512)
        file_storage.seek(pos)
        kind = imghdr.what(None, head)
        if kind not in {"png", "jpeg"}:
            raise ValueError("Geçersiz görsel içeriği")
