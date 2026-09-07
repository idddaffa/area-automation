import arcpy
import os
import csv

# ==============================================================================
# PARAMETER INPUT DARI ARCGIS TOOLBOX
# ==============================================================================
input_txt = arcpy.GetParameterAsText(0)      # File .txt / .csv
output_poly = arcpy.GetParameterAsText(1)    # Output Feature Class Poligon
output_points = arcpy.GetParameterAsText(2)  # Output Feature Class Titik
sr_input = arcpy.GetParameterAsText(3)       # Spatial Reference (Sistem Koordinat)

def clean_str(val):
    """Membersihkan spasi dan tanda petik ganda/tunggal dari teks."""
    if val is None:
        return ""
    return str(val).strip().strip('"\'')

def detect_delimiter(file_path):
    """Mendeteksi apakah file menggunakan pemisah Tab, Titik Koma, atau Koma."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        elif ';' in first_line:
            return ';'
        else:
            return ','

def setup_feature_classes(out_pts, out_poly, spatial_ref):
    """Membuat Feature Class Titik dan Poligon beserta field atributnya."""
    # 1. Buat Layer Titik
    folder_pts, name_pts = os.path.split(out_pts)
    arcpy.CreateFeatureclass_management(folder_pts, name_pts, "POINT", spatial_reference=spatial_ref)
    
    pts_fields = [
        ["WILAYAH", "TEXT", "", "", 100],
        ["KEGIATAN", "TEXT", "", "", 100],
        ["KATEGORI", "TEXT", "", "", 100],
        ["NAMA_AREA", "TEXT", "", "", 100],
        ["BATAS_WILAYAH", "TEXT", "", "", 50],
        ["TITIK", "TEXT", "", "", 50]
    ]
    
    if hasattr(arcpy.management, "AddFields"):
        arcpy.management.AddFields(out_pts, pts_fields)
    else:
        for f in pts_fields:
            arcpy.AddField_management(out_pts, f[0], f[1], field_length=f[4])

    # 2. Buat Layer Poligon
    folder_poly, name_poly = os.path.split(out_poly)
    arcpy.CreateFeatureclass_management(folder_poly, name_poly, "POLYGON", spatial_reference=spatial_ref)
    
    poly_fields = [
        ["WILAYAH", "TEXT", "", "", 100],
        ["KEGIATAN", "TEXT", "", "", 100],
        ["KATEGORI", "TEXT", "", "", 100],
        ["NAMA_AREA", "TEXT", "", "", 100]
    ]
    
    if hasattr(arcpy.management, "AddFields"):
        arcpy.management.AddFields(out_poly, poly_fields)
    else:
        for f in poly_fields:
            arcpy.AddField_management(out_poly, f[0], f[1], field_length=f[4])

def txt_to_automation(txt_file, out_poly, out_pts, spatial_ref):
    arcpy.env.overwriteOutput = True
    
    arcpy.AddMessage("1. Menyiapkan Feature Class output...")
    setup_feature_classes(out_pts, out_poly, spatial_ref)
    
    delimiter = detect_delimiter(txt_file)
    data_map = {}
    skipped_rows = []
    
    # --------------------------------------------------------------------------
    # 2. BACA FILE NOTEPAD & PLOT TITIK
    # --------------------------------------------------------------------------
    arcpy.AddMessage("2. Membaca data koordinat dan membuat titik...")
    pts_insert_fields = ["SHAPE@XY", "WILAYAH", "KEGIATAN", "KATEGORI", "NAMA_AREA", "BATAS_WILAYAH", "TITIK"]
    
    with arcpy.da.InsertCursor(out_pts, pts_insert_fields) as pts_cursor:
        with open(txt_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)  # Lewati baris header judul kolom
            
            for line_no, row in enumerate(reader, start=2):
                if not row or not any(clean_str(field) for field in row):
                    continue  # Lewati baris kosong
                
                if len(row) < 8:
                    skipped_rows.append(f"Baris {line_no}: Kolom kurang dari 8.")
                    continue
                
                try:
                    wilayah = clean_str(row[0])
                    kegiatan = clean_str(row[1])
                    kategori = clean_str(row[2])
                    area = clean_str(row[3])
                    batas = clean_str(row[4]).upper()
                    titik = clean_str(row[5])
                    
                    lon = float(clean_str(row[6]).replace(',', '.'))
                    lat = float(clean_str(row[7]).replace(',', '.'))
                    
                    # Tulis Titik ke Feature Class
                    pts_cursor.insertRow([(lon, lat), wilayah, kegiatan, kategori, area, batas, titik])
                    
                    # Kelompokkan titik untuk pembuatan poligon
                    key = (area, batas)
                    if key not in data_map:
                        data_map[key] = {
                            "area": area, 
                            "batas": batas, 
                            "pts": [],
                            "wilayah": wilayah, 
                            "kegiatan": kegiatan, 
                            "kategori": kategori
                        }
                    data_map[key]["pts"].append(arcpy.Point(lon, lat))
                    
                except ValueError as err:
                    skipped_rows.append(f"Baris {line_no}: Format koordinat salah ({err})")
                    continue

    if skipped_rows:
        arcpy.AddWarning(f"Terdapat {len(skipped_rows)} baris yang dilewati karena format tidak sesuai:")
        for w in skipped_rows[:5]:
            arcpy.AddWarning(f"  - {w}")
        if len(skipped_rows) > 5:
            arcpy.AddWarning(f"  - ...dan {len(skipped_rows) - 5} baris lainnya.")

    # --------------------------------------------------------------------------
    # 3. PEMBUATAN POLIGON & AUTO-BOLONG SPASIAL (.difference)
    # --------------------------------------------------------------------------
    arcpy.AddMessage("3. Membentuk poligon dan memproses lubang (INNER)...")
    
    outers_list = []
    inners_list = []

    for (area, batas), info in data_map.items():
        pnts = info["pts"]
        if len(pnts) < 3:
            arcpy.AddWarning(f"Area '{area}' ({batas}) memiliki kurang dari 3 titik, poligon dilewati.")
            continue
        
        # Pastikan cincin koordinat tertutup (Snap closure)
        if pnts[0].X != pnts[-1].X or pnts[0].Y != pnts[-1].Y:
            pnts.append(pnts[0])
            
        geom = arcpy.Polygon(arcpy.Array(pnts), spatial_ref)
        
        if "INNER" in batas:
            inners_list.append(geom)
        else:
            outers_list.append({
                "geom": geom,
                "wilayah": info["wilayah"],
                "kegiatan": info["kegiatan"],
                "kategori": info["kategori"],
                "area": area
            })

    # Tulis Poligon ke Feature Class dengan memotong area INNER secara spasial
    poly_insert_fields = ["SHAPE@", "WILAYAH", "KEGIATAN", "KATEGORI", "NAMA_AREA"]
    with arcpy.da.InsertCursor(out_poly, poly_insert_fields) as poly_cursor:
        for item in outers_list:
            outer_geom = item["geom"]
            
            # Setiap INNER yang posisinya berada di dalam / menimpa OUTER ini akan langsung memotongnya
            for inner_geom in inners_list:
                if not outer_geom.disjoint(inner_geom):
                    outer_geom = outer_geom.difference(inner_geom)
            
            poly_cursor.insertRow([
                outer_geom, 
                item["wilayah"], 
                item["kegiatan"], 
                item["kategori"], 
                item["area"]
            ])

    arcpy.AddMessage("SELESAI! Layer Titik dan Poligon berhasil dibuat dengan sempurna.")

if __name__ == "__main__":
    txt_to_automation(input_txt, output_poly, output_points, sr_input)
