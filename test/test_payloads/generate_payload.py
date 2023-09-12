import json

samplers = ['Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM++ 2M', 'DPM++ SDE', 'DPM++ 2M SDE', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras', 'DPM++ 2M Karras', 'DPM++ SDE Karras', 'DPM++ 2M SDE Karras']

params_file = 'txt2img.json' #'payload.json'
f = open(params_file)
payload = json.load(f)

for sampler in samplers:
    payload['sampler_name'] = sampler
    payload_file_name = params_file.split('.')[0] + '_' + sampler + '.json'
    out_file = open(payload_file_name, "w")
    json.dump(payload, out_file, indent = 6)
    out_file.close()