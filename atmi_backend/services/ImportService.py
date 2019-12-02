import json
import os

import h5py
import numpy as np

from atmi_backend.config import DATA_ROOT
from atmi_backend.db_interface.InitialService import InitialService
from atmi_backend.db_interface.LabelService import LabelService
from atmi_backend.db_interface.SeriesService import SeriesService
from atmi_backend.db_interface.StudiesService import StudiesService
from atmi_backend.services.SeriesExtractionService import SeriesExtractionService


class ImportService:
    def __init__(self, connection):
        self.conn = connection

    def import_dcm(self, instance_id, data_path):
        series_extraction_service = SeriesExtractionService()
        all_series_list = series_extraction_service.extract_series_from_path(os.path.join(DATA_ROOT, data_path))
        study_service = StudiesService(self.conn)
        series_service = SeriesService(self.conn)

        for suid in all_series_list:
            series = all_series_list[suid]
            patient_uid = 0
            study_uid = 0
            study_service.insert(instance_id, patient_uid, study_uid, suid, "[]", 0)
            study = study_service.query({"instance_id": instance_id, "suid": suid})
            study = study[0]
            total_files_number = 0
            folder_name_arr = []
            for series_path in series:
                folder_name_arr.append(series_path)
                one_series = series[series_path][0]
                patient_uid = one_series.info.PatientID
                study_uid = one_series.info.StudyID
                # disp_name = "pid:" + one_series.info.PatientID + "_sid:" + one_series.info.StudyID
                total_files_number += one_series.length
                series_info = one_series.info
                if len(one_series.shape) == 2:
                    z_dim = 1
                    x_dim = one_series.shape[0]
                    y_dim = one_series.shape[1]
                else:
                    z_dim = one_series.shape[0]
                    x_dim = one_series.shape[1]
                    y_dim = one_series.shape[2]

                series_service.insert(study['study_id'], one_series.description, series_path, one_series.filenames,
                                      one_series.length, series_info.get("WindowWidth"),
                                      series_info.get("WindowCenter"), one_series.sampling[1], one_series.sampling[1],
                                      one_series.sampling[0], x_dim, y_dim, z_dim, series_info.get("PatientID"),
                                      series_info.get("SeriesInstanceUID"), series_info.get("StudyDate") or "", "",
                                      "")

            study_service.update({"instance_id": instance_id, "suid": suid},
                                 {"total_files_number": total_files_number, "patient_uid": patient_uid,
                                  "study_uid": study_uid, "folder_name": str(folder_name_arr)})

        return True

    def import_annotations(self, load_type, annotation_path, erase_old=True):
        """
        Load saved annotations.
        Please be caution!
        This operation will firstly erase old masks if not set erase_old as False and then replace with the new one.
        :param load_type: 'h5'|'mhd'
        :param annotation_path:
        :param erase_old:
        :return:
        """
        LV_code = 2
        if load_type == "h5":
            labeldb = h5py.File(annotation_path, 'r')
            studyService = StudiesService(self.conn)
            seriesService = SeriesService(self.conn)
            labelService = LabelService(self.conn)
            for study_id in labeldb.keys():
                study_uid = study_id[6:]
                for series_id in labeldb[study_id].keys():
                    series_uid = series_id[7:]
                    series = seriesService.query({"series_instance_uid": series_uid})
                    if len(series) > 0:
                        slice_file_name = eval(series[0]['series_files_list'])
                        content_3D = labeldb[f"{study_id}/{series_id}/label"]
                        for i in range(len(slice_file_name)):
                            content_2D = content_3D[:, :, i]
                            x_dim = content_2D.shape[0]
                            y_dim = content_2D.shape[1]
                            content_1D = np.reshape(content_2D, x_dim * y_dim)
                            content_1D[content_1D > 0] = LV_code
                            unique_id = np.unique(content_1D).tolist()
                            compressed_content_1D = LabelService.compress_content(content_1D)
                            content = {
                                "labelmap2D": {"pixelData": compressed_content_1D, "segmentsOnLabelmap": unique_id, "dataLength":content_1D.shape[0]}}
                            labelService.insert(series[0]['series_id'], 1, slice_file_name[i],
                                                str.encode(json.dumps(content)))

        elif load_type == 'mhd':
            raise NotImplementedError()


if __name__ == "__main__":
    ini_service = InitialService()
    importService = ImportService(ini_service.get_connection())
    importService.import_annotations("h5", "tests/tool/1.2.840.114350.2.232.2.798268.2.81188688.1.h5")

# http://127.0.0.1:5000/load_data/2/NYU_CMR_Raw
# http://127.0.0.1:5000/export_label/studies/2


