import math


def step_by_step_line(x1: int, y1: int, x2: int, y2: int, with_trace: bool = False):
    pixels = []
    trace = []
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        pixels.append((x1, y1, 1.0))
        if with_trace:
            trace.append((0, x1, y1, 1.0, "dx = 0, dy = 0"))
        return pixels, trace

    floor = math.floor
    if abs(dx) >= abs(dy):
        k = dy / dx
        b = y1 - k * x1
        step = 1 if x2 >= x1 else -1
        for i, x in enumerate(range(x1, x2 + step, step)):
            y_exact = k * x + b
            y = floor(y_exact + 0.5)
            pixels.append((x, y, 1.0))
            if with_trace:
                trace.append((i, x, y, 1.0, f"k={k:.4f}, b={b:.4f}, y={y_exact:.4f} -> {y}"))
    else:
        k_inv = dx / dy
        b_inv = x1 - k_inv * y1
        step = 1 if y2 >= y1 else -1
        for i, y in enumerate(range(y1, y2 + step, step)):
            x_exact = k_inv * y + b_inv
            x = floor(x_exact + 0.5)
            pixels.append((x, y, 1.0))
            if with_trace:
                trace.append((i, x, y, 1.0, f"k_inv={k_inv:.4f}, b_inv={b_inv:.4f}, x={x_exact:.4f} -> {x}"))

    return pixels, trace


def dda_line(x1: int, y1: int, x2: int, y2: int, with_trace: bool = False):
    pixels = []
    trace = []
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        pixels.append((x1, y1, 1.0))
        if with_trace:
            trace.append((0, x1, y1, 1.0, "L = 0"))
        return pixels, trace

    x_inc = dx / steps
    y_inc = dy / steps
    x = float(x1)
    y = float(y1)
    floor = math.floor

    for i in range(steps + 1):
        px = floor(x + 0.5)
        py = floor(y + 0.5)
        pixels.append((px, py, 1.0))
        if with_trace:
            trace.append((i, px, py, 1.0, f"x={x:.4f}, y={y:.4f}, dx_step={x_inc:.4f}, dy_step={y_inc:.4f}"))
        x += x_inc
        y += y_inc

    return pixels, trace


def bresenham_line(x1: int, y1: int, x2: int, y2: int, with_trace: bool = False):
    pixels = []
    trace = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else (-1 if x1 > x2 else 0)
    sy = 1 if y1 < y2 else (-1 if y1 > y2 else 0)
    x = x1
    y = y1

    if dx >= dy:
        err = (dy << 1) - dx
        d1 = dy << 1
        d2 = (dy - dx) << 1
        for i in range(dx + 1):
            pixels.append((x, y, 1.0))
            if with_trace:
                trace.append((i, x, y, 1.0, f"e={err} (dx={dx}, dy={dy})"))
            if err >= 0:
                y += sy
                err += d2
            else:
                err += d1
            x += sx
    else:
        err = (dx << 1) - dy
        d1 = dx << 1
        d2 = (dx - dy) << 1
        for i in range(dy + 1):
            pixels.append((x, y, 1.0))
            if with_trace:
                trace.append((i, x, y, 1.0, f"e={err} (dx={dx}, dy={dy})"))
            if err >= 0:
                x += sx
                err += d2
            else:
                err += d1
            y += sy

    return pixels, trace


def bresenham_circle(xc: int, yc: int, radius: int, with_trace: bool = False):
    pixels = []
    trace = []
    r = abs(radius)
    if r == 0:
        pixels.append((xc, yc, 1.0))
        if with_trace:
            trace.append((0, xc, yc, 1.0, "R = 0"))
        return pixels, trace

    x = 0
    y = r
    d = 3 - (r << 1)
    step = 0
    while x <= y:
        pixels.extend([
            (xc + x, yc + y, 1.0),
            (xc - x, yc + y, 1.0),
            (xc + x, yc - y, 1.0),
            (xc - x, yc - y, 1.0),
            (xc + y, yc + x, 1.0),
            (xc - y, yc + x, 1.0),
            (xc + y, yc - x, 1.0),
            (xc - y, yc - x, 1.0),
        ])
        if with_trace:
            trace.append((step, xc + x, yc + y, 1.0, f"d={d}, (x={x}, y={y}) + 8 октантов"))
        if d < 0:
            d += (x << 2) + 6
        else:
            d += ((x - y) << 2) + 10
            y -= 1
        x += 1
        step += 1

    return pixels, trace


def castle_pitteway_line(x1: int, y1: int, x2: int, y2: int, with_trace: bool = False):
    pixels = [(x1, y1, 1.0)]
    trace = []
    dx = x2 - x1
    dy = y2 - y1
    adx = abs(dx)
    ady = abs(dy)
    if adx == 0 and ady == 0:
        if with_trace:
            trace.append((0, x1, y1, 1.0, "dx = 0, dy = 0"))
        return pixels, trace

    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
    if adx >= ady:
        a, b = adx, ady
        s_dx, s_dy = sx, 0
        d_dx, d_dy = sx, sy
    else:
        a, b = ady, adx
        s_dx, s_dy = 0, sy
        d_dx, d_dy = sx, sy

    cx = x1
    cy = y1
    if with_trace:
        trace.append((0, cx, cy, 1.0, f"Старт (a={a}, b={b})"))

    if b == 0:
        for i in range(1, a + 1):
            cx += s_dx
            cy += s_dy
            pixels.append((cx, cy, 1.0))
            if with_trace:
                trace.append((i, cx, cy, 1.0, "Шаг s (прямой)"))
        return pixels, trace

    if a == b:
        for i in range(1, a + 1):
            cx += d_dx
            cy += d_dy
            pixels.append((cx, cy, 1.0))
            if with_trace:
                trace.append((i, cx, cy, 1.0, "Шаг d (диагональный)"))
        return pixels, trace

    x = a - b
    y = b
    m1 = "s"
    m2 = "d"
    while x != y:
        if x > y:
            x -= y
            m2 = m1 + m2[::-1]
        else:
            y -= x
            m1 = m2 + m1[::-1]

    pattern = m2 + m1[::-1]
    moves = pattern * x
    for i, ch in enumerate(moves, start=1):
        if ch == "s":
            cx += s_dx
            cy += s_dy
        else:
            cx += d_dx
            cy += d_dy
        pixels.append((cx, cy, 1.0))
        if with_trace:
            trace.append((i, cx, cy, 1.0, f"Код='{ch}', НОД={x}, паттерн='{pattern}'"))

    return pixels, trace


def wu_line(x1: int, y1: int, x2: int, y2: int, with_trace: bool = False):
    pixels = []
    trace = []
    if x1 == x2 and y1 == y2:
        pixels.append((x1, y1, 1.0))
        if with_trace:
            trace.append((0, x1, y1, 1.0, "Точка"))
        return pixels, trace

    steep = abs(y2 - y1) > abs(x2 - x1)
    if steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    dx = x2 - x1
    dy = y2 - y1
    gradient = dy / dx if dx != 0 else 1.0
    step = 0

    if steep:
        pixels.append((y1, x1, 1.0))
        if with_trace:
            trace.append((step, y1, x1, 1.0, f"Начало (steep=True, grad={gradient:.4f})"))
            step += 1
    else:
        pixels.append((x1, y1, 1.0))
        if with_trace:
            trace.append((step, x1, y1, 1.0, f"Начало (steep=False, grad={gradient:.4f})"))
            step += 1

    intery = y1 + gradient
    floor = math.floor

    if steep:
        for x in range(x1 + 1, x2):
            iy = floor(intery)
            f = intery - iy
            rf = 1.0 - f
            pixels.append((iy, x, rf))
            if f > 0.0:
                pixels.append((iy + 1, x, f))
            if with_trace:
                trace.append((step, iy, x, rf, f"interx={intery:.4f}, rfpart={rf:.4f}, fpart={f:.4f}"))
                step += 1
                if f > 0.0:
                    trace.append((step, iy + 1, x, f, f"Парный пиксель: alpha={f:.4f}"))
                    step += 1
            intery += gradient
        pixels.append((y2, x2, 1.0))
        if with_trace:
            trace.append((step, y2, x2, 1.0, "Конец отрезка"))
    else:
        for x in range(x1 + 1, x2):
            iy = floor(intery)
            f = intery - iy
            rf = 1.0 - f
            pixels.append((x, iy, rf))
            if f > 0.0:
                pixels.append((x, iy + 1, f))
            if with_trace:
                trace.append((step, x, iy, rf, f"intery={intery:.4f}, rfpart={rf:.4f}, fpart={f:.4f}"))
                step += 1
                if f > 0.0:
                    trace.append((step, x, iy + 1, f, f"Парный пиксель: alpha={f:.4f}"))
                    step += 1
            intery += gradient
        pixels.append((x2, y2, 1.0))
        if with_trace:
            trace.append((step, x2, y2, 1.0, "Конец отрезка"))

    return pixels, trace
