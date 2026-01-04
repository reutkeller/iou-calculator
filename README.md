# IoU Calculator for QGIS

## Description
This plugin provides a comprehensive accuracy analysis tool for vector polygons. It is specifically designed to evaluate the performance of object detection or segmentation models by comparing "Ground Truth" layers against "Prediction" layers.

## Features
* **Area-Based Analysis:** Calculates global IoU, Dice Coefficient, Precision, and Recall based on the total overlapping area.
* **Object-Based Analysis:** Performs polygon-to-polygon matching using a spatial index to calculate mIoU and F1-Score.
* **Visual Feedback:** Automatically generates a "Crosshatch" overlap layer and a per-polygon IoU score layer.
* **Summary Table:** Exports all metrics into a non-spatial attribute table for easy reporting.

## Calculation Logic
1.  **Intersection over Union (IoU):** Defined as $Area\ of\ Overlap\ /\ Area\ of\ Union$.
2.  **Object Matching:** A prediction is counted as a **True Positive (TP)** if its IoU with a Ground Truth polygon exceeds the user-defined threshold (default 0.50).

## Requirements
* QGIS 3.0 or higher.
* All layers should be in the same Projected Coordinate System (CRS) for accurate area calculations.

## License
Licensed under GNU GPL v2.