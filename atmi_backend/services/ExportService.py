import os
import time

import h5py
import numpy as np
import pydicom
from flask import Flask

from atmi_backend.config import OUTPUT_ROOT
from atmi_backend.db_interface.InstanceService import InstanceService
from atmi_backend.db_interface.LabelService import LabelService
from atmi_backend.db_interface.SeriesService import SeriesService
from atmi_backend.db_interface.StudiesService import StudiesService

# log = logging.getLogger(__name__)
app = Flask("atmi.app")


class ExportService:
    def __init__(self, connection):
        self.conn = connection

    def save_studies(self, instance_id, split_entry_num=100, store_type="train", save_label=True, save_data=True, compression=None):
        """
        Save all annotations and and dicom data for each study in the instance
        :param instance_id:
        :param split_entry_num: create new h5 file if stored entries more than the max split number
        :param store_type: train or test
        :param save_label: True or False
        :param save_data: True or False
        :param compression: Whether the hdf5 file compressed or not. "gzip|lzf"
        :return:
        """
        msg_box = []
        instance_service = InstanceService(self.conn)
        instance = instance_service.query({"instance_id": instance_id})
        instance_name = instance[0]['name']
        study_service = StudiesService(self.conn)
        studies = study_service.query({"instance_id": instance_id})
        study_num = 0
        study_h5 = None
        time_stamp = str(int(time.time()))
        for study in studies:

            study_id = study['study_id']
            app.logger.info(f"Save study-instance_id:{instance_id}({instance_name}),study_id:{study_id}")
            h5_path = os.path.join(OUTPUT_ROOT, str(instance_id))
            if study_num % split_entry_num == 0:
                if not os.path.exists(h5_path):
                    os.makedirs(h5_path)
                if study_h5 is not None:
                    study_h5.close()
                h5_file_name = f"Export-{instance_id}-{instance_name}-{time_stamp}-{study_num // split_entry_num}.h5"
                study_h5 = h5py.File(os.path.join(h5_path, h5_file_name), 'w')

            if save_label:
                self.save_onestudy_label(study_id, study, study_h5, msg_box, store_type, compression)

            if save_data:
                self.save_onestudy_dcm(study_id, study, study_h5, msg_box, store_type, compression)

            study_num += 1

        study_h5.close()
        return msg_box

    def save_onestudy_label(self, study_id, study, study_h5, msg_box, store_type="train", compression=None):
        series_service = SeriesService(self.conn)
        label_service = LabelService(self.conn)
        series = series_service.query({"study_id": study_id})
        for i in series:
            series_id = i['series_id']
            series_uuid = i['series_instance_uid']
            x_dim = int(i['x_dimension'])
            y_dim = int(i['y_dimension'])
            z_dim = int(i['z_dimension'])
            series_files_list = eval(i['series_files_list'])
            series_label = np.zeros((x_dim, y_dim, z_dim))
            labels = label_service.query({"series_id": series_id})
            if len(labels) == 0:
                app.logger.debug(f"The current series don't have labels:{i['series_id']}")
                continue
            for label in labels:
                file_id = label['file_id']
                content = eval(label['content'])
                pixel_data = content['labelmap2D']['pixelData']

                for label in pixel_data:
                    pixel_data_xy = np.zeros((x_dim,y_dim))
                    label_int = int(float(label))
                    content_1D = np.reshape(pixel_data_xy, x_dim * y_dim)
                    content_1D[pixel_data[label]] = label_int
                    pixel_data_xy = np.reshape(content_1D, (x_dim, y_dim))

                    z_index = series_files_list.index(file_id)
                    series_label[:, :, z_index] += pixel_data_xy

            label_db = study_h5.create_dataset(f"{store_type}/study:{study['suid']}-series:{series_uuid}/label",
                                               data=series_label, compression=compression)
            label_db.attrs['x_spacing'] = i['x_spacing']
            label_db.attrs['y_spacing'] = i['y_spacing']
            label_db.attrs['z_spacing'] = i['z_spacing']
            label_db.attrs['patient_id'] = i['patient_id']
            label_db.attrs['files'] = i['series_files_list']
            label_db.attrs['path'] = i['series_path']
            label_db.attrs['series_id'] = i['series_id']
            label_db.attrs['study_id'] = i['study_id']
            label_db.attrs['description'] = i["series_description"]
            app.logger.debug(f"Save one series - path:{i['series_path']}, series_id:{i['series_id']}, "
                             f"h5path: study:{study['suid']}/series:{series_uuid}/label")
            msg_box.append(f"Save one series - path:{i['series_path']}, series_id:{i['series_id']}, "
                           f"h5path: study:{store_type}/{study['suid']}-series:{series_uuid}/label")

        return msg_box

    def save_onestudy_dcm(self, study_id, study, study_h5, msg_box, store_type="train", compression=None):
        series_service = SeriesService(self.conn)
        series = series_service.query({"study_id": study_id})
        for i in series:
            # Load DICOM data.
            series_uuid = i['series_instance_uid']
            file_list = [os.path.join(i['series_path'], file_name) for file_name in eval(i['series_files_list'])]
            series_dcm = []
            try:
                for file in file_list:
                    file_dcm = pydicom.dcmread(file, force=True)
                    series_dcm.append(file_dcm.pixel_array)
            except Exception as e:
                app.logger.warn(f"Read dicom file error: {file}, series uuid:{series_uuid}, with error:{e}")
                continue

            series_dcm = np.stack(series_dcm)
            series_dcm = np.moveaxis(series_dcm, 0, -1)

            # if the dimension of original dicom and label mismatch should throw an error, and log.
            # if series_dcm.shape != series_label.shape:
            #     app.logger.warn(
            #         f"The original DICOM shape({series_dcm.shape}) mismatch with the label's shape({series_label.shape})")
            dcm = study_h5.create_dataset(f"{store_type}/study:{study['suid']}-series:{series_uuid}/data",
                                          data=series_dcm, compression=compression)
            dcm.attrs['x_spacing'] = i['x_spacing']
            dcm.attrs['y_spacing'] = i['y_spacing']
            dcm.attrs['z_spacing'] = i['z_spacing']
            dcm.attrs['patient_id'] = i['patient_id']
            dcm.attrs['files'] = i['series_files_list']
            dcm.attrs['path'] = i['series_path']
            dcm.attrs['series_id'] = i['series_id']
            dcm.attrs['study_id'] = i['study_id']
            dcm.attrs['description'] = i["series_description"]
            msg_box.append(f"Save one series - path:{i['series_path']}, series_id:{i['series_id']}, "
                           f"h5path: {store_type}/study:{study['suid']}-series:{series_uuid}/data")

        return msg_box
