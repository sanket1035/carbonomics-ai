"""Draw the misty pine-forest picture that fills the big "carbonomics" wordmark on the landing page.

Fully procedural (fixed seed), so no stock photo or licence is involved: layered conifers, blurred by distance,
with fog between the layers. Output: dashboard/public/wordmark-forest.webp
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 2400, 464
rng = np.random.default_rng(7)
root = os.path.join(os.path.dirname(__file__), "..")


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky():
    top, bot = (30, 62, 57), (132, 182, 170)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(top, bot, y / H))
    return img


def conifer(d, x, base, h, w, color):
    """One conifer: a stack of drooping, ragged tiers on a thin trunk."""
    d.line([(x, base), (x, base - h)], fill=color, width=max(2, int(w * 0.06)))
    tiers = int(h / 14) + 4
    for k in range(tiers):
        t = k / tiers
        y = base - h + t * h * 0.98
        half = w * (0.10 + 0.9 * t) / 2
        drop = h / tiers * 2.1
        pts = [(x, y - drop * 0.35)]
        n = 5
        for s in range(n + 1):  # ragged right edge going down
            f = s / n
            pts.append((x + half * (0.35 + 0.65 * f) + rng.normal(0, half * 0.07), y + drop * (f * 0.9) + rng.normal(0, 1.5)))
        pts.append((x, y + drop * 0.55))
        for s in range(n, -1, -1):  # ragged left edge going up
            f = s / n
            pts.append((x - half * (0.35 + 0.65 * f) + rng.normal(0, half * 0.07), y + drop * (f * 0.9) + rng.normal(0, 1.5)))
        d.polygon(pts, fill=color)


def layer(base, hmin, hmax, step, color, blur, right_bias):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = -30.0
    while x < W + 30:
        p = x / W
        if rng.random() < 0.35 + right_bias * p:  # forest gets denser towards the right
            h = rng.uniform(hmin, hmax) * (1 + 0.25 * p * right_bias)
            conifer(d, x, base + rng.uniform(-6, 6), h, h * rng.uniform(0.34, 0.5), color + (255,))
        x += step * rng.uniform(0.6, 1.3)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


def fog(strength, y0, y1, left_extra):
    a = np.zeros((H, W), np.float32)
    ys = np.arange(H)[:, None]
    band = np.exp(-((ys - (y0 + y1) / 2) ** 2) / (2 * ((y1 - y0) / 2) ** 2))
    xs = np.linspace(0, 1, W)[None, :]
    a = band * strength * (1 + left_extra * (1 - xs))
    noise = np.array(Image.fromarray((rng.random((H // 8, W // 8)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    a = np.clip(a * (0.75 + 0.5 * noise), 0, 1)
    im = np.zeros((H, W, 4), np.uint8)
    im[..., :3] = (150, 198, 186)
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


img = sky().convert("RGBA")
# far mountains
mt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(mt)
xs = np.arange(0, W + 40, 40)
ridge = 260 + 28 * np.sin(xs / 260) + 18 * np.sin(xs / 90 + 1) + rng.normal(0, 4, len(xs))
d.polygon([(0, H)] + list(zip(xs, ridge)) + [(W, H)], fill=(92, 144, 133, 255))
img.alpha_composite(mt.filter(ImageFilter.GaussianBlur(5)))
img.alpha_composite(fog(0.7, 200, 330, 0.5))
# conifer layers, far to near
for base, hmin, hmax, step, col, blur, bias, fg in [
    (330, 90, 150, 26, (100, 154, 142), 3.2, 0.2, 0.40),
    (370, 120, 210, 30, (84, 136, 124), 2.2, 0.35, 0.28),
    (410, 170, 290, 38, (64, 120, 108), 1.2, 0.5, 0.16),
    (470, 250, 420, 52, (38, 88, 79), 0.5, 0.6, 0.05),
]:
    img.alpha_composite(layer(base, hmin, hmax, step, col, blur, bias))
    img.alpha_composite(fog(fg, base - hmax * 0.8, base - 10, 1.6))
img.alpha_composite(fog(0.22, H * 0.35, H * 0.8, 1.2))  # soft haze in the middle, strongest on the left
out = img.convert("RGB")
out = Image.blend(out, out.filter(ImageFilter.GaussianBlur(0.8)), 0.25)
out.save(os.path.join(root, "dashboard/public/wordmark-forest.webp"), quality=86)
print("wrote wordmark-forest.webp", os.path.getsize(os.path.join(root, "dashboard/public/wordmark-forest.webp")) // 1024, "KB")
