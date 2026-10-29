import os
import struct

def parse_png(file_path, file):
    try:
        file.seek(-12, 2)
        end_chunk = file.read(8)
        if end_chunk[4:8] != b'IEND':
            return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}
        
        file.seek(8)
        width = height = bit_depth = 0
        resolution = "96x96"
        compression_str = "Deflate"
        
        while True:
            length_bytes = file.read(4)
            if not length_bytes or len(length_bytes) < 4:
                break
            chunk_len = struct.unpack(">I", length_bytes)[0]
            chunk_type = file.read(4)
            
            if chunk_type == b'IHDR':
                width, height, bit_depth, color_type, comp = struct.unpack(">IIBBB", file.read(11))
                if comp != 0:
                    compression_str = str(comp)
                file.seek(chunk_len - 11 + 4, 1)
            elif chunk_type == b'pHYs':
                if chunk_len == 9:
                    ppu_x, ppu_y, unit = struct.unpack(">IIB", file.read(9))
                    if unit == 1:
                        resolution = f"{int(ppu_x * 0.0254)}x{int(ppu_y * 0.0254)}"
                    else:
                        resolution = f"{ppu_x}x{ppu_y}"
                    file.seek(4, 1)
                else:
                    file.seek(chunk_len + 4, 1)
            elif chunk_type == b'IEND':
                break
            else:
                file.seek(chunk_len + 4, 1)
                
        return {
            "format": "PNG",
            "compression": compression_str,
            "size": f"{width}x{height}",
            "resolution": resolution,
            "color_depth": f"{bit_depth} bit"
        }
    except Exception:
        return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

def parse_jpg(file_path, file):
    try:
        file.seek(-2, 2)
        if file.read(2) != b'\xff\xd9':
            return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}
        
        file.seek(2)
        resolution = "96x96"
        width = height = color_depth = 0
        compression_str = "JPEG"
        
        while True:
            marker = file.read(2)
            if not marker or len(marker) < 2:
                break
            if marker[0] != 0xFF:
                break
                
            if marker[1] == 0xE0:
                length = struct.unpack(">H", file.read(2))[0]
                identifier = file.read(5)
                if identifier == b'JFIF\x00':
                    version, units, x_density, y_density = struct.unpack(">HBBB", file.read(5))
                    if units in (1, 2):
                        resolution = f"{x_density}x{y_density}"
                    file.seek(length - 2 - 5 - 5, 1)
                else:
                    file.seek(length - 2 - 5, 1)
            elif marker[1] in [0xC0, 0xC1, 0xC2]:
                if marker[1] == 0xC0:
                    compression_str = "Baseline"
                elif marker[1] == 0xC2:
                    compression_str = "Progressive"
                    
                length = struct.unpack(">H", file.read(2))[0]
                precision, height, width = struct.unpack(">BHH", file.read(5))
                color_depth = precision * 3
                file.seek(length - 2 - 5, 1)
            else:
                length = struct.unpack(">H", file.read(2))[0]
                file.seek(length - 2, 1)
                
        return {
            "format": "JPEG",
            "compression": compression_str,
            "size": f"{width}x{height}",
            "resolution": resolution,
            "color_depth": f"{color_depth} bit"
        }
    except Exception:
        return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

def parse_bmp(file_path, file):
    try:
        file.seek(0, 2)
        actual_size = file.tell()
        
        file.seek(2)
        declared_size = struct.unpack("<I", file.read(4))[0]
        if declared_size > actual_size:
            return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}
            
        file.seek(14)
        dib_header_size = struct.unpack("<I", file.read(4))[0]
        width, height, planes, bpp = struct.unpack("<IIHH", file.read(12))
        compression_method = struct.unpack("<I", file.read(4))[0]
        file.seek(12, 1)
        h_res, v_res = struct.unpack("<II", file.read(8))
        
        dpi_x = int(h_res * 0.0254) if h_res > 0 else 0
        dpi_y = int(v_res * 0.0254) if v_res > 0 else 0
        
        if dpi_x > 0 and dpi_y > 0:
            resolution = f"{dpi_x}x{dpi_y}"
        else:
            resolution = "96x96"
            
        comp_str = "Без сжатия"
        if compression_method == 1:
            comp_str = "RLE8"
        elif compression_method == 2:
            comp_str = "RLE4"
        
        return {
            "format": "BMP",
            "compression": comp_str,
            "size": f"{width}x{height}",
            "resolution": resolution,
            "color_depth": f"{bpp} bit"
        }
    except Exception:
        return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

def parse_gif(file_path, file):
    try:
        file.seek(6)
        width, height, packed = struct.unpack("<HHB", file.read(5))
        color_resolution = ((packed & 0b01110000) >> 4) + 1
        return {
            "format": "GIF",
            "compression": "LZW",
            "size": f"{width}x{height}",
            "resolution": "96x96",
            "color_depth": f"{color_resolution * 3} bit"
        }
    except Exception:
        return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

def parse_tif(file_path, file):
    try:
        file.seek(0)
        header = file.read(8)
        if header[:2] == b'II':
            endian = '<'
        elif header[:2] == b'MM':
            endian = '>'
        else:
            return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

        magic = struct.unpack(endian + 'H', header[2:4])[0]
        if magic != 42:
            return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

        ifd_offset = struct.unpack(endian + 'I', header[4:8])[0]
        file.seek(ifd_offset)

        num_entries = struct.unpack(endian + 'H', file.read(2))[0]

        width = height = 0
        x_res_off = y_res_off = 0
        res_unit = 2
        compression_val = 1
        bits_per_sample = 8
        samples_per_pixel = 1
        bits_is_array = False
        bits_offset = 0

        for _ in range(num_entries):
            entry = file.read(12)
            if len(entry) < 12:
                break
            tag, field_type, count, value_offset = struct.unpack(endian + 'HHII', entry)

            val_short = struct.unpack(endian + 'H', entry[8:10])[0]
            val_long = value_offset

            val = val_short if field_type == 3 else val_long

            if tag == 256:
                width = val
            elif tag == 257:
                height = val
            elif tag == 258:
                if count == 1:
                    bits_per_sample = val
                else:
                    bits_is_array = True
                    bits_offset = value_offset
            elif tag == 259:
                compression_val = val
            elif tag == 277:
                samples_per_pixel = val
            elif tag == 282:
                x_res_off = value_offset
            elif tag == 283:
                y_res_off = value_offset
            elif tag == 296:
                res_unit = val

        if bits_is_array and bits_offset > 0:
            current_pos = file.tell()
            file.seek(bits_offset)
            bits_per_sample = struct.unpack(endian + 'H', file.read(2))[0]
            file.seek(current_pos)

        color_depth = bits_per_sample * samples_per_pixel

        dpi_x = dpi_y = 96
        if x_res_off > 0:
            file.seek(x_res_off)
            num, den = struct.unpack(endian + 'II', file.read(8))
            if den != 0:
                dpi_x = int(num / den)
        if y_res_off > 0:
            file.seek(y_res_off)
            num, den = struct.unpack(endian + 'II', file.read(8))
            if den != 0:
                dpi_y = int(num / den)

        if res_unit == 3:
            dpi_x = int(dpi_x * 2.54)
            dpi_y = int(dpi_y * 2.54)

        comp_str = "Без сжатия"
        if compression_val == 5:
            comp_str = "LZW"
        elif compression_val in (6, 7):
            comp_str = "JPEG"
        elif compression_val == 32773:
            comp_str = "PackBits"
        elif compression_val in (2, 3, 4):
            comp_str = "CCITT"
        elif compression_val == 8:
            comp_str = "Deflate"

        return {
            "format": "TIFF",
            "compression": comp_str,
            "size": f"{width}x{height}",
            "resolution": f"{dpi_x}x{dpi_y}",
            "color_depth": f"{color_depth} bit"
        }

    except Exception:
        return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}

def get_image_metadata(file_path):
    try:
        with open(file_path, "rb") as file:
            file.seek(0, 2)
            if file.tell() < 12:
                return {"format": "Битый", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}
            file.seek(0)

            signature = file.read(8)
            if signature.startswith(b'\x89PNG\r\n\x1a\n'):
                return parse_png(file_path, file)
            elif signature.startswith(b'\xff\xd8'):
                return parse_jpg(file_path, file)
            elif signature.startswith(b'BM'):
                return parse_bmp(file_path, file)
            elif signature.startswith(b'GIF87a') or signature.startswith(b'GIF89a'):
                return parse_gif(file_path, file)
            elif signature.startswith(b'II*\x00') or signature.startswith(b'MM\x00*'):
                return parse_tif(file_path, file)
            else:
                return {"format": "Не поддерживается", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}
    except Exception:
        return {"format": "Ошибка", "compression": "-", "size": "-", "resolution": "-", "color_depth": "-"}