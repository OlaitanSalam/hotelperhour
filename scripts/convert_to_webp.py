from PIL import Image
from pathlib import Path

src = Path(r"C:\Users\USER\VScodes Projects\HotelPerHour\static\images")
if not src.exists():
    print('static/images not found')
    raise SystemExit(1)

for p in list(src.glob('*.jpg')) + list(src.glob('*.jpeg')):
    out = p.with_suffix('.webp')
    try:
        img = Image.open(p)
        img.save(out, 'WEBP', quality=80, method=6)
        print(f'Converted {p.name} -> {out.name}')
    except Exception as e:
        print('Failed', p.name, e)
