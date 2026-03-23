from assessments.models import AssessmentFile
from assessments.tasks import process_assessment_file_task
import json

failed = AssessmentFile.objects.filter(processing_status='failed')
print(f'Reprocessing {failed.count()} files.')

category_map = {
    'radiography_image': 'image',
    'clinical_notes': 'report',
    'labs': 'labs',
    'vitals': 'vitals'
}
queue_map = {
    'image': 'image_queue',
    'report': 'report_queue',
    'labs': 'labs_queue',
    'vitals': 'vitals_queue'
}

for f in failed:
    f.processing_status = 'processing'
    f.save()
    ms_name = category_map.get(f.data_category)
    meta = f.metadata or {}
    view_pos = meta.get('view_label', 'PA') if ms_name == 'image' else None
    process_assessment_file_task.apply_async(args=[f.id, ms_name, view_pos], queue=queue_map.get(ms_name))
    print(f'Retried {f.id}')
