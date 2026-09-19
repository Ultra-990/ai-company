"""Fixed local graph only. Never accepts URLs, paths, nodes or commands from callers."""
import http.client
import json
from urllib.parse import urlencode

PROFILE = 'z-image-turbo-768.v1'
MAX_IMAGE = 8 * 1024 * 1024


def graph(prompt, seed, prefix):
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'z_image_turbo_bf16.safetensors', 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'qwen_3_4b.safetensors', 'type': 'lumina2', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'ae.safetensors'}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['2', 0]}},
        '5': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['4', 0]}},
        '6': {'class_type': 'EmptySD3LatentImage', 'inputs': {'width': 768, 'height': 512, 'batch_size': 1}},
        '7': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0], 'shift': 3.0}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['7', 0], 'positive': ['4', 0], 'negative': ['5', 0],
              'latent_image': ['6', 0], 'seed': seed, 'steps': 8, 'cfg': 1.0,
              'sampler_name': 'res_multistep', 'scheduler': 'simple', 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'SaveImage', 'inputs': {'images': ['9', 0], 'filename_prefix': prefix}},
    }


class ComfyFailure(ValueError):
    pass


class ComfyRejected(ComfyFailure):
    """Server explicitly rejected graph validation before enqueueing."""


class ComfyProvider:
    def request(self, path, payload=None, binary=False):
        # Loopback literal, no proxies, redirects or retries. Timeout is per I/O.
        conn = http.client.HTTPConnection('127.0.0.1', 8188, timeout=5)
        try:
            body = None if payload is None else json.dumps(payload).encode()
            conn.request('GET' if payload is None else 'POST', path, body,
                         {'Content-Type': 'application/json'})
            response = conn.getresponse()
            limit = MAX_IMAGE if binary else 1024 * 1024
            raw = response.read(limit + 1)
            if path == '/prompt' and response.status == 400 and len(raw) <= limit:
                rejection = json.loads(raw)
                if isinstance(rejection, dict) and 'error' in rejection and 'node_errors' in rejection:
                    raise ComfyRejected('comfy_graph_rejected')
            if response.status != 200 or len(raw) > limit:
                raise ComfyFailure('comfy_response_invalid')
            return raw if binary else json.loads(raw)
        except ComfyRejected:
            raise
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise ComfyFailure('comfy_unavailable_or_invalid') from exc
        finally:
            conn.close()

    def prepare(self):
        from app.services.local_ollama import ensure_idle
        try:
            ensure_idle()  # Does not unload any model.
        except ValueError as exc:
            raise ComfyFailure('ollama_busy') from exc
        queue = self.request('/queue')
        if queue.get('queue_running') != [] or queue.get('queue_pending') != []:
            raise ComfyFailure('comfy_busy')
        # This profile was tested on this installed server version, including prompt_id support.
        stats = self.request('/system_stats')
        if stats.get('system', {}).get('comfyui_version') != '0.35.0':
            raise ComfyFailure('comfy_version_changed')
        for node, field, name in [('UNETLoader', 'unet_name', 'z_image_turbo_bf16.safetensors'),
                                 ('CLIPLoader', 'clip_name', 'qwen_3_4b.safetensors'),
                                 ('VAELoader', 'vae_name', 'ae.safetensors')]:
            try:
                info = self.request('/object_info/' + node)
                if name not in info[node]['input']['required'][field][0]:
                    raise ComfyFailure('comfy_models_missing')
            except (KeyError, TypeError) as exc:
                raise ComfyFailure('comfy_models_missing') from exc
        return stats

    def submit(self, prompt_id, workflow):
        data = self.request('/prompt', {'prompt_id': prompt_id, 'client_id': prompt_id, 'prompt': workflow})
        if data.get('prompt_id') != prompt_id or data.get('node_errors'):
            raise ComfyFailure('comfy_submission_uncertain')

    def history(self, prompt_id):
        return self.request('/history/' + prompt_id).get(prompt_id)

    def image(self, prompt_id, entry):
        # Only a file produced by this job's SaveImage, never arbitrary local files.
        import re
        filename = entry.get('filename', '')
        if (entry.get('type') != 'output' or entry.get('subfolder') != 'AI-Company'
                or not isinstance(filename, str)
                or not re.fullmatch(re.escape(prompt_id) + r'_\d+_?\.png', filename)):
            raise ComfyFailure('unexpected_output_path')
        return self.request('/view?' + urlencode({'filename': filename,
            'subfolder': 'AI-Company', 'type': 'output'}), binary=True)
