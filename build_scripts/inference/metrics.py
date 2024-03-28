#!/usr/bin/env python
import os

from aws_xray_sdk.core import patch_all
from aws_xray_sdk.core import xray_recorder

patch_all()

service_startup_time = os.getenv('SERVICE_STARTUP_TIME', '2')
service_init_time = os.getenv('SERVICE_INIT_TIME', '3')
dependency_installation_time = os.getenv('DEPENDENCY_INSTALLATION_TIME', '4')

xray_recorder.configure(service='EsdEndpoint')

with xray_recorder.in_segment('EndpointLaunch') as segment:
    with xray_recorder.in_subsegment('ServiceStartup') as subsegment:
        subsegment.put_annotation('duration', service_startup_time)

    with xray_recorder.in_subsegment('ServiceInit') as subsegment:
        subsegment.put_annotation('duration', service_init_time)

    with xray_recorder.in_subsegment('DependencyInstallation') as subsegment:
        subsegment.put_annotation('duration', dependency_installation_time)

    current_trace_id = segment.trace_id

    print('Trace ID: {}'.format(current_trace_id))
