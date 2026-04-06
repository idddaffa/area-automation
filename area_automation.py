import arcpy
import os
import re

input_txt = arcpy.GetParameterAsText(0)
output_poly = arcpy.GetParameterAsText(1)
output_points = arcpy.GetParameterAsText(2)
sr_input = arcpy.GetParameterAsText(3) 

def clean_str(val):
    return val.replace('"', '').replace("'", "").strip()

def txt_to_automation(txt_file, out_poly, out_pts, spatial_ref):
    arcpy.env.outputCoordinateSystem = spatial_ref
    arcpy.env.XYTolerance = "0.000000001 DecimalDegrees"
    arcpy.env.XYResolution = "0.0000000001 DecimalDegrees"
    arcpy.env.overwriteOutput = True
    
    # 1. SETUP OUTPUT TITIK
    folder, name = os.path.split(out_pts)
    arcpy.CreateFeatureclass_management(folder, name, "POINT", spatial_reference=spatial_ref)
    
    fields_list = ["WILAYAH", "KATEGORI", "JENIS_PENYISIHAN", "NAMA_AREA", "BATAS_WILAYAH", "TITIK"]
    for f in fields_list:
        arcpy.AddField_management(out_pts, f, "TEXT")

    data_map = {}
    skipped = 0
    
    # 2. EKSTRAKSI DATA NOTEPAD
    insert_fields = ["SHAPE@XY"] + fields_list
    with arcpy.da.InsertCursor(out_pts, insert_fields) as cursor:
        with open(txt_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if i == 0 or not line.strip(): continue 
                
                if '\t' in line: parts = line.split('\t')
                elif ';' in line: parts = line.split(';')
                else: parts = line.split(',')
                    
                if len(parts) < 8:
                    skipped += 1
                    continue
                
                try:
                    wilayah = clean_str(parts[0])
                    kategori = clean_str(parts[1])
                    jenis = clean_str(parts[2])
                    area = clean_str(parts[3])
                    batas = clean_str(parts[4])
                    titik = clean_str(parts[5])
                    
                    lon_str = clean_str(parts[6]).replace(',', '.')
                    lat_str = clean_str(parts[7]).replace(',', '.')
                    lon = float(lon_str)
                    lat = float(lat_str)
                    
                    # Plot Titik
                    cursor.insertRow([(lon, lat), wilayah, kategori, jenis, area, batas, titik])
                    
                    # Simpan struktur untuk Poligon
                    pnt = arcpy.Point(lon, lat)
                    key = f"{area}_{batas}"
                    if key not in data_map:
                        data_map[key] = {
                            "area_original": area, "type": batas, "pts": [], 
                            "wilayah": wilayah, "kategori": kategori, "jenis": jenis
                        }
                    data_map[key]["pts"].append(pnt)
                except Exception:
                    skipped += 1
                    continue

    if skipped > 0:
        arcpy.AddError(f"FATAL: Ada {skipped} baris gagal dibaca. Pastikan format copy-paste menggunakan Tab murni.")
        raise arcpy.ExecuteError()

    # 3. SETUP OUTPUT POLIGON (DENGAN LOGIKA AUTO-BOLONG)
    folder_poly, name_poly = os.path.split(out_poly)
    arcpy.CreateFeatureclass_management(folder_poly, name_poly, "POLYGON", spatial_reference=spatial_ref)
    
    poly_fields_list = ["WILAYAH", "KATEGORI", "JENIS_PENYISIHAN", "NAMA_AREA"]
    for f in poly_fields_list:
        arcpy.AddField_management(out_poly, f, "TEXT")

    poly_insert_fields = ["SHAPE@"] + poly_fields_list
    with arcpy.da.InsertCursor(out_poly, poly_insert_fields) as poly_cursor:
        area_groups = {}
        for key, info in data_map.items():
            pnts = info["pts"]
            if len(pnts) < 3: continue
            
            # Kunci presisi agar menempel (Snap)
            if pnts[0].X != pnts[-1].X or pnts[0].Y != pnts[-1].Y:
                pnts.append(pnts[0])
                
            arr = arcpy.Array(pnts)
            
            # --- LOGIKA AUTO-BOLONG ---
            # Jika batasnya INNER, potong nama areanya (Misal "Area I.1" otomatis jadi "Area I")
            if "INNER" in info["type"].upper():
                parent_area = re.split(r'[.-]', info["area_original"])[0].strip()
            else:
                parent_area = info["area_original"]
            
            if parent_area not in area_groups:
                area_groups[parent_area] = {
                    "arrays": [], 
                    "wilayah": info["wilayah"], 
                    "kategori": info["kategori"], 
                    "jenis": info["jenis"]
                }
                
            # Pastikan Array OUTER selalu di index 0, INNER ditambahkan di belakangnya sebagai lubang
            if "OUTER" in info["type"].upper():
                area_groups[parent_area]["arrays"].insert(0, arr)
            else:
                area_groups[parent_area]["arrays"].append(arr)

        # Build dan Insert Geometri Poligon
        for parent_area, attrs in area_groups.items():
            poly_geom = arcpy.Polygon(arcpy.Array(attrs["arrays"]), spatial_ref)
            poly_cursor.insertRow([poly_geom, attrs["wilayah"], attrs["kategori"], attrs["jenis"], parent_area])

    arcpy.AddMessage("SUKSES! Area Inner berhasil memotong Area Outer secara otomatis.")

if __name__ == "__main__":
    txt_to_automation(input_txt, output_poly, output_points, sr_input)