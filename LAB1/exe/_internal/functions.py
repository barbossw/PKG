def rgb_to_cmyk(r, g, b):
    r_prime, g_prime, b_prime = r / 255.0, g / 255.0, b / 255.0
    k = 1 - max(r_prime, g_prime, b_prime)
    if k == 1.0:
        return 0, 0, 0, 100
    c = (1 - r_prime - k) / (1 - k)
    m = (1 - g_prime - k) / (1 - k)
    y = (1 - b_prime - k) / (1 - k)
    return int(round(c * 100)), int(round(m * 100)), int(round(y * 100)), int(round(k * 100))

def cmyk_to_rgb(c, m, y, k):
    c, m, y, k = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return int(round(r)), int(round(g)), int(round(b))

def rgb_to_lab(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
    r, g, b = r * 100, g * 100, b * 100

    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    x, y, z = x / 95.047, y / 100.000, z / 108.883
    fx = x ** (1/3) if x > 0.008856 else (7.787 * x) + (16 / 116)
    fy = y ** (1/3) if y > 0.008856 else (7.787 * y) + (16 / 116)
    fz = z ** (1/3) if z > 0.008856 else (7.787 * z) + (16 / 116)

    l = (116 * fy) - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    
    return int(round(l)), int(round(a)), int(round(b_val))

def lab_to_rgb(l, a, b_val):
    fy = (l + 16) / 116
    fx = a / 500 + fy
    fz = fy - b_val / 200

    x = fx ** 3 if fx ** 3 > 0.008856 else (fx - 16 / 116) / 7.787
    y = fy ** 3 if fy ** 3 > 0.008856 else (fy - 16 / 116) / 7.787
    z = fz ** 3 if fz ** 3 > 0.008856 else (fz - 16 / 116) / 7.787

    x, y, z = x * 95.047, y * 100.000, z * 108.883

    x, y, z = x / 100.0, y / 100.0, z / 100.0
    r = x * 3.2406 + y * -1.5372 + z * -0.4986
    g = x * -0.9689 + y * 1.8758 + z * 0.0415
    b = x * 0.0557 + y * -0.2040 + z * 1.0570


    r = 1.055 * (r ** (1 / 2.4)) - 0.055 if r > 0.0031308 else 12.92 * r
    g = 1.055 * (g ** (1 / 2.4)) - 0.055 if g > 0.0031308 else 12.92 * g
    b = 1.055 * (b ** (1 / 2.4)) - 0.055 if b > 0.0031308 else 12.92 * b


    r, g, b = r * 255, g * 255, b * 255

    warning = False
    if round(r) < 0 or round(r) > 255 or round(g) < 0 or round(g) > 255 or round(b) < 0 or round(b) > 255:
        warning = True
    
    r = max(0, min(255, round(r)))
    g = max(0, min(255, round(g)))
    b = max(0, min(255, round(b)))
    
    return int(r), int(g), int(b), warning

def cmyk_to_lab(c, m, y, k):
    c, m, y, k = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    
    return rgb_to_lab(r, g, b)

def lab_to_cmyk(l, a, b_val):
    r, g, b, warning = lab_to_rgb(l, a, b_val)
    c, m, y, k = rgb_to_cmyk(r, g, b)
    return c, m, y, k, warning