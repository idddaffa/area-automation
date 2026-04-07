# Area Automation Tool 🗺️

**High-Precision Coordinate to Working Area (Polygon) Generator**

A custom Python tool built with **ArcPy** to automate the creation of Point and Polygon feature classes from tabular coordinate data. Designed to streamline geospatial data workflows where precision and topological rules (such as inner/outer boundaries) are critical, particularly for mapping operational or working areas.

## ✨ Key Features

* **Auto-Donut Polygons**: Smartly detects `INNER` boundaries and automatically clips them from the parent `OUTER` area to create perfect donut polygons without manual editing.
* **High-Precision Plotting**: Overrides default ArcGIS geoprocessing tolerances to maintain coordinate accuracy up to 12 decimal places (0.000000001 degrees), preventing unintended snapping or geometry shifting.
* **Dynamic Projection**: Allows users to dynamically set the target Coordinate Reference System (CRS) during execution to prevent datum shifts.
* **Automated Attribute Mapping**: Seamlessly extracts tabular data (Region, Category, Area Name, etc.) and injects it directly into the generated Feature Class Attribute Tables.
* **Failsafe Execution**: Built-in data validation that halts execution and alerts the user if the raw text data format is broken or missing mandatory columns.

## 📂 Data Input Format

The tool expects a Tab-separated `.txt` file with the following 8 columns:

| REGION | CATEGORY | EXCLUSION_TYPE | AREA_NAME | BOUNDARY_TYPE | POINT | LONGITUDE | LATITUDE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SALAZAR | RETAIN | PSWK ARTICLE 3.1 | Area I | OUTER | A | 130.833... | -1.200... |
| SALAZAR | RETAIN | PSWK ARTICLE 3.1 | Area I | INNER | A-In | 130.910... | -1.220... |

*(Tip: Copy data directly from your spreadsheet software to an empty Notepad file to preserve the pure Tab delimiters).*

## 🚀 How to Use in ArcGIS Pro

1. Clone or download this repository.
2. Open ArcGIS Pro and navigate to the **Catalog** pane.
3. Connect to the repository folder and locate `AreaAutomation.atbx`.
4. Double-click the **Area Automation** script tool.
5. Define the parameters:
   * **Input Notepad File**: Select your `.txt` data.
   * **Output Polygon**: Define the target Geodatabase path for the polygon layer.
   * **Output Point**: Define the target Geodatabase path for the point layer.
   * **Coordinate System**: Select the spatial reference or copy it directly from an existing map layer to ensure perfect alignment.
6. Click **Run**.

## 🛠️ Requirements
* ArcGIS Pro (Tested on 3.x)
* Python 3 (ArcGIS Default Environment with `arcpy` module)

## 📸 Visual Demo

![Coordinates to Area Automation](https://github.com/user-attachments/assets/11ba2d0a-2524-4276-90e6-a7f0773949a3)

*Watch the tool automatically process tabular coordinates and generate perfect donut polygons in seconds.*
