"""图片验证码工具：生成随机字符并绘制带干扰的 PNG 图片。"""
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

# 去掉易混淆字符（0/O、1/I）
CAPTCHA_CHARS = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


# 入参 length 为字符个数（默认 4），返回该长度的随机验证码字符串
def generate_code(length=4):
    """生成随机验证码字符串。"""
    return ''.join(random.choice(CAPTCHA_CHARS) for _ in range(length))


# 入参为字号，返回可用的字体对象；按候选路径依次尝试，全部失败时使用 PIL 内置默认字体
def _load_font(size):
    """优先使用系统字体，失败时回退到 PIL 默认字体。"""
    for path in ('C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/arial.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# 入参为验证码字符串与画布尺寸，返回 PNG 格式的图片字节流（供 HttpResponse 直接输出）；
# 通过干扰线、干扰点、随机颜色与位移防止简单的机器识别。
def create_captcha_image(code, width=120, height=40):
    """绘制验证码图片并返回 PNG 字节流。"""
    image = Image.new('RGB', (width, height), (248, 249, 251))
    draw = ImageDraw.Draw(image)
    font = _load_font(26)

    # 干扰线
    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=(random.randint(150, 210), random.randint(150, 210), 180), width=1)

    # 干扰点
    for _ in range(60):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(120, 200), random.randint(120, 200), random.randint(120, 200)),
        )

    # 逐字符绘制，带随机颜色与轻微位移
    step = width // (len(code) + 1)
    for index, char in enumerate(code):
        color = (random.randint(20, 90), random.randint(20, 90), random.randint(120, 200))
        x = step * (index + 1) - 8 + random.randint(-3, 3)
        y = random.randint(2, 6)
        draw.text((x, y), char, font=font, fill=color)

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()
