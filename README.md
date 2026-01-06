# IoU Calculator for QGIS 
<img src="imgs/visualization_scores.png" width="400">  

## Description

![Alt text](logo_IoU.png) 
IoU Calculator for QGIS is a plugin designed for accuracy assessment of vector polygon datasets. It enables robust evaluation of object detection and segmentation results by comparing ground truth layers with predicted layers.

The calculation methodology follows the approach used in the RAMP project for building detection (https://rampml.global/) in the object calculation method.
## Features
* **Area-Based Analysis:** Calculates global IoU, Dice Coefficient, Precision, and Recall based on the total overlapping area.
* **Object-Based Analysis:** Performs polygon-to-polygon matching using a spatial index to calculate mIoU and F1-Score. The user needs to define minimal  threshold that will be used to define minimum overlap to decide what is matching. 
* **Visual Output:** Automatically generates a overlap layer and a per-polygon IoU score layer.
* **Summary Table:** Exports all metrics into a non-spatial attribute table for easy reporting.

## Calculation Logic
1.  **Intersection over Union (IoU):** Defined as $Area\ of\ Overlap\ /\ Area\ of\ Union$.
2.  **Object Matching:** A prediction is counted as a **True Positive (TP)** if its IoU with a Ground Truth polygon exceeds the user-defined threshold (default 0.50).

## Output
Polygons before calculation :   
<img src="imgs/polygons_for_calc.png" width="400">

Overlap layer :  


<img src="imgs/intersect_area.png" width="400">
  
Result Table (summary for all the geometries) :  
  
<img src="imgs/resu_table.png" width="400">

  
  *IoU value can be displayed per polygon  

## Requirements
* QGIS 3.0 or higher.
* All layers should be in the same Projected Coordinate System (CRS) for accurate area calculations.

## License
Licensed under GNU GPL v2.