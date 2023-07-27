import sys
from unittest import TestCase


class MmeUtilsTest(TestCase):

    def test_read_from_s3(self):
        from utils import read_from_s3
        content = read_from_s3('s3://sd-release-test-sddreamboothtr-aigcbucketa457cb49-dhvez2qft7lj/txt2img/infer_v2/1690443798.119154/api_param.json')
        import json
        def parse_constant(c: str) -> float:
            if c == "NaN":
                raise ValueError("NaN is not valid JSON")

            if c == 'Infinity':
                return sys.float_info.max

            return float(c)

        print(json.loads(content, parse_constant=parse_constant))

    def test_checkspace_and_update_models(self):
        selected_models = {
            'space_free_size': 40000000000.0,  # sys.float_info.max
            'Stable-diffusion': [
                {
                    's3': 's3://sd-release-test-sddreamboothtr-aigcbucketa457cb49-dhvez2qft7lj/Stable-diffusion/checkpoint/release-test-01/67bfa613-4c53-471e-aeaf-ba7525884c88',
                    'id': '67bfa613-4c53-471e-aeaf-ba7525884c88',
                    'model_name': 'v1-5-pruned-emaonly.safetensors',
                    'type': 'Stable-diffusion'
                }
            ]
        }
        import mme_utils
        mme_utils.download_and_update = lambda *args, **kwargs: print(f'download {args}')
        from mme_utils import checkspace_and_update_models

        checkspace_and_update_models(selected_models)
