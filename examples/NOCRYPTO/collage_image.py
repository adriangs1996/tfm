import datetime
from PIL import Image
from io import BytesIO
from django.core.files import File
from pillow_heif import register_heif_opener


def open_image_resize_and_orientate(path, default_width, default_height):
    register_heif_opener()
    photo = Image.open(path).convert("RGB")
    exif = photo.getexif()
    orientation = exif.get(0x0112)
    # tipos de orientacion de la foto original
    # 2: Image.FLIP_LEFT_RIGHT,
    # 3: Image.ROTATE_180,
    # 4: Image.FLIP_TOP_BOTTOM,
    # 5: Image.TRANSPOSE,
    # 6: Image.ROTATE_270,
    # 7: Image.TRANSVERSE,
    # 8: Image.ROTATE_90,
    if orientation == 6:
        photo = photo.rotate(270, resample=Image.BICUBIC, expand=True)
    elif orientation == 3:
        photo = photo.rotate(180, resample=Image.BICUBIC, expand=True)
    elif orientation == 8:
        photo = photo.rotate(90, resample=Image.BICUBIC, expand=True)
    photo = photo.resize((default_width, default_height))
    return photo


def create_challenger_collage(challenger_challenge):

    collage = Image.new("RGB", (2200, 2590), color=(255, 255, 255, 255))

    # Image size
    default_height = 1280
    default_width = 720
    # Y positions
    y1 = 10
    y2 = 1300
    # X positions
    x1 = 10
    x2 = 740
    x3 = 1470

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.initial_front_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x1, y1)
    )

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.initial_side_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x2, y1)
    )

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.initial_back_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x3, y1)
    )

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.final_front_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x1, y2)
    )

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.final_side_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x2, y2)
    )

    collage.paste(
        open_image_resize_and_orientate(
            path=challenger_challenge.final_back_photo,
            default_width=default_width,
            default_height=default_height
        ),
        (x3, y2)
    )

    thumb_io = BytesIO()
    collage.save(thumb_io, 'JPEG')
    current_datetime = datetime.datetime.now()
    random_name_to_file = f'collage_{challenger_challenge.id}_{current_datetime.strftime("%Y%m%d_%H%M%S")}.jpg'
    thumbnail = File(thumb_io, name=random_name_to_file)

    challenger_challenge.image = thumbnail
    challenger_challenge.save()
