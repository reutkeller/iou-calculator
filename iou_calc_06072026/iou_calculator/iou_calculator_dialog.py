import os
import datetime
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsSpatialIndex,
    QgsFeatureRequest,
    QgsFillSymbol,
    QgsLinePatternFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer
)
import processing
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QColor

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'iou_calculator_dialog_base.ui')
)

class IoUCalculatorDialog(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(IoUCalculatorDialog, self).__init__(parent)
        self.setupUi(self)
        self.CalcBut.clicked.connect(self.run_analysis)

    def write_log(self, text, level="info"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        color = "black"
        if level == "error":
            color = "red"
        elif level == "success":
            color = "green"

        self.logBox.appendHtml(
            f"<b>[{time_str}]</b> <span style='color:{color}'>{text}</span>"
        )
        self.logBox.ensureCursorVisible()
        QApplication.processEvents()

    def apply_crosshatch_symbology(self, layer):
        """Applies a professional cross-hatch pattern for overlaps"""
        symbol = QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_style': 'no'})
        symbol.deleteSymbolLayer(0)

        line_layer1 = QgsLinePatternFillSymbolLayer()
        line_layer1.setLineAngle(45)
        line_layer1.setDistance(2.0)
        line_layer1.setLineWidth(0.26)
        line_layer1.setColor(QColor("black"))

        line_layer2 = QgsLinePatternFillSymbolLayer()
        line_layer2.setLineAngle(135)
        line_layer2.setDistance(2.0)
        line_layer2.setLineWidth(0.26)
        line_layer2.setColor(QColor("black"))

        border_layer = QgsSimpleLineSymbolLayer()
        border_layer.setColor(QColor("black"))
        border_layer.setWidth(0.4)

        symbol.appendSymbolLayer(line_layer1)
        symbol.appendSymbolLayer(line_layer2)
        symbol.appendSymbolLayer(border_layer)

        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()

    def run_analysis(self):
        self.logBox.clear()
        self.progressBar.setValue(0)
        self.write_log("Initializing full accuracy analysis...")

        calc_area = self.area_based.isChecked()
        calc_obj = self.object_based.isChecked()
        iou_threshold = self.threshold_input.value()

        gt_layer = self.GroundTruth.currentLayer()
        pd_layer = self.Predictions.currentLayer()

        if not gt_layer or not pd_layer:
            self.write_log("Please select both GT and Prediction layers.", "error")
            return

        results_data = []

        # ---------------------------------------------------------
        # 1. AREA-BASED IoU
        # ---------------------------------------------------------
        if calc_area:
            try:
                self.write_log("Running Area-Based calculations...")
                intersect = processing.run("native:intersection", {
                    "INPUT": gt_layer, "OVERLAY": pd_layer, "OUTPUT": "memory:raw_ov"
                })["OUTPUT"]

                dissolved = processing.run("native:dissolve", {
                    "INPUT": intersect, "OUTPUT": "memory:dissolved_ov"
                })["OUTPUT"]

                area_gt = sum(f.geometry().area() for f in gt_layer.getFeatures())
                area_pd = sum(f.geometry().area() for f in pd_layer.getFeatures())
                area_ov = sum(f.geometry().area() for f in dissolved.getFeatures())

                union = area_gt + area_pd - area_ov
                iou_a = area_ov / union if union > 0 else 0
                prec_a = area_ov / area_pd if area_pd > 0 else 0
                rec_a = area_ov / area_gt if area_gt > 0 else 0
                dice_a = (2 * area_ov) / (area_gt + area_pd) if (area_gt + area_pd) > 0 else 0

                results_data.extend([
                    ("Area_IoU", iou_a), ("Area_Dice", dice_a),
                    ("Area_Precision", prec_a), ("Area_Recall", rec_a)
                ])

                # Visualization
                dissolved.setName(f"Area_Overlap_{gt_layer.name()}")
                QgsProject.instance().addMapLayer(dissolved)
                self.apply_crosshatch_symbology(dissolved)

                # ONE-ROW LOG
                area_msg = f"<b>Area Results:</b> IoU: {iou_a:.4f} | Dice: {dice_a:.4f} | Prec: {prec_a:.4f} | Rec: {rec_a:.4f}"
                self.write_log(area_msg, "success")

            except Exception as e:
                self.write_log(f"Area-based error: {e}", "error")

        # ---------------------------------------------------------
        # 2. OBJECT-BASED IoU
        # ---------------------------------------------------------
        if calc_obj:
            try:
                self.write_log("Running Object-Based calculations...")
                self.progressBar.setValue(40)

                gt_features = list(gt_layer.getFeatures())
                pd_features = list(pd_layer.getFeatures())
                n_gt, n_pd = len(gt_features), len(pd_features)
                
                gt_lookup = {f.id(): f for f in gt_features}
                gt_spatial_index = QgsSpatialIndex()
                for feat in gt_features:
                    gt_spatial_index.insertFeature(feat)

                tp_count = 0
                matched_gt_ids = set()
                all_best_ious = []

                for pd_feat in pd_features:
                    pd_geom = pd_feat.geometry()
                    best_iou_for_pred = 0
                    best_gt_id_for_pred = -1

                    candidates = gt_spatial_index.intersects(pd_geom.boundingBox())
                    for gt_id in candidates:
                        if gt_id in matched_gt_ids: continue
                        gt_f = gt_lookup.get(gt_id)
                        if not gt_f: continue

                        inter = pd_geom.intersection(gt_f.geometry()).area()
                        if inter <= 0: continue

                        union = pd_geom.area() + gt_f.geometry().area() - inter
                        iou = inter / union if union > 0 else 0

                        if iou > best_iou_for_pred:
                            best_iou_for_pred = iou
                            best_gt_id_for_pred = gt_id

                    all_best_ious.append(best_iou_for_pred)
                    if best_gt_id_for_pred != -1 and best_iou_for_pred >= iou_threshold:
                        tp_count += 1
                        matched_gt_ids.add(best_gt_id_for_pred)

                # Spatial Result Layer (Per-polygon scores)
                spatial_results = pd_layer.materialize(QgsFeatureRequest())
                spatial_results.setName(f"IoU_Scores_{pd_layer.name()}")
                prov = spatial_results.dataProvider()
                prov.addAttributes([QgsField("iou_score", QVariant.Double)])
                spatial_results.updateFields()
                idx = spatial_results.fields().indexFromName("iou_score")
                spatial_results.startEditing()
                for i, f in enumerate(spatial_results.getFeatures()):
                    val = all_best_ious[i] if i < len(all_best_ious) else 0
                    spatial_results.changeAttributeValue(f.id(), idx, round(val, 4))
                spatial_results.commitChanges()
                QgsProject.instance().addMapLayer(spatial_results)

                # Metrics Calculation
                obj_prec = tp_count / n_pd if n_pd > 0 else 0
                obj_rec = tp_count / n_gt if n_gt > 0 else 0
                f1_denom = obj_prec + obj_rec
                f1_obj = (2 * obj_prec * obj_rec) / f1_denom if f1_denom > 0 else 0
                mIoU = sum(all_best_ious) / len(all_best_ious) if all_best_ious else 0

                results_data.extend([
                    ("Object_mIoU", mIoU), ("Object_F1_Score", f1_obj),
                    ("Object_Precision", obj_prec), ("Object_Recall", obj_rec),
                    (f"TP_at_{iou_threshold}", tp_count), ("FP", n_pd - tp_count),
                    ("FN", n_gt - tp_count), ("GT_Count", n_gt), ("PD_Count", n_pd)
                ])

                # ONE-ROW LOG
                obj_msg = f"<b>Object Results:</b> mIoU: {mIoU:.4f} | F1: {f1_obj:.4f} | Prec: {obj_prec:.4f} | Rec: {obj_rec:.4f} | TP: {tp_count}"
                self.write_log(obj_msg, "success")

            except Exception as e:
                self.write_log(f"Object-based error: {e}", "error")

        # ---------------------------------------------------------
        # 3. FINAL SUMMARY TABLE
        # ---------------------------------------------------------
        self.progressBar.setValue(90)
        result_table = QgsVectorLayer("NoGeometry", "Accuracy_Summary_Table", "memory")
        tbl_prov = result_table.dataProvider()
        tbl_prov.addAttributes([QgsField("Metric", QVariant.String), QgsField("Value", QVariant.Double)])
        result_table.updateFields()

        table_feats = []
        for name, val in results_data:
            f = QgsFeature()
            f.setAttributes([name, round(val, 4)])
            table_feats.append(f)

        tbl_prov.addFeatures(table_feats)
        QgsProject.instance().addMapLayer(result_table)

        self.progressBar.setValue(100)
        self.write_log("Analysis complete. Layers added to project.", "info")
        QtWidgets.QMessageBox.information(self, "Success", "Analysis complete. Check the log window and new layers for details.")