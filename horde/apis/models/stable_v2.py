# SPDX-FileCopyrightText: 2022 Konstantinos Thoukydidis <mail@dbzer0.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import copy

from flask_restx import fields

from horde.apis.models import v2
from horde.consts import KNOWN_POST_PROCESSORS, KNOWN_SAMPLERS, KNOWN_WORKFLOWS
from horde.vars import horde_title


class ImageParsers(v2.Parsers):
    def __init__(self):
        super().__init__()
        self.generate_parser.add_argument(
            "censor_nsfw",
            type=bool,
            default=True,
            required=False,
            help="If the request is SFW, and the worker accidentally generates NSFW, it will send back a censored image.",
            location="json",
        )
        self.generate_parser.add_argument(
            "source_image",
            type=str,
            required=False,
            help="The Base64-encoded webp to use for img2img.",
            location="json",
        )
        self.generate_parser.add_argument(
            "source_processing",
            type=str,
            default="img2img",
            required=False,
            help="If source_image is provided, specifies how to process it.",
            location="json",
        )
        self.generate_parser.add_argument(
            "source_mask",
            type=str,
            required=False,
            help=(
                "If img_processing is set to 'inpainting' or 'outpainting', "
                "this parameter can be optionally provided as the mask of the areas to inpaint. "
                "If this arg is not passed, the inpainting/outpainting mask has to be embedded as alpha channel."
            ),
            location="json",
        )
        self.generate_parser.add_argument(
            "models",
            type=list,
            required=False,
            default=["stable_diffusion"],
            help="The acceptable models with which to generate.",
            location="json",
        )
        self.generate_parser.add_argument(
            "r2",
            type=bool,
            default=True,
            required=False,
            help="If True, the image will be sent via cloudflare r2 download link.",
            location="json",
        )
        self.generate_parser.add_argument(
            "shared",
            type=bool,
            default=False,
            required=False,
            help=(
                "If True, The image will be shared with LAION for improving their dataset. "
                "This will also reduce your kudos consumption by 2. For anonymous users, this is always True."
            ),
            location="json",
        )
        self.generate_parser.add_argument(
            "replacement_filter",
            type=bool,
            default=True,
            required=False,
            help="If enabled, suspicious prompts are sanitized through a string replacement filter instead.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "max_pixels",
            type=int,
            required=False,
            default=512 * 512,
            help="The maximum amount of pixels this worker can generate.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "blacklist",
            type=list,
            required=False,
            help="Specifies the words that this worker will not accept in a prompt.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_img2img",
            type=bool,
            required=False,
            default=True,
            help="If True, this worker will pick up img2img requests.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_painting",
            type=bool,
            required=False,
            default=True,
            help="If True, this worker will pick up inpainting/outpaining requests.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_unsafe_ipaddr",
            type=bool,
            required=False,
            default=True,
            help="If True, this worker will pick up img2img requests coming from clients with an unsafe IP.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_post_processing",
            type=bool,
            required=False,
            default=True,
            help="If True, this worker will pick up requests requesting post-processing.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_controlnet",
            type=bool,
            required=False,
            default=False,
            help="If True, this worker will pick up requests requesting ControlNet.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_sdxl_controlnet",
            type=bool,
            required=False,
            default=False,
            help="If True, this worker will pick up requests requesting SDXL ControlNet.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "allow_lora",
            type=bool,
            required=False,
            default=False,
            help="If True, this worker will pick up requests requesting LoRas.",
            location="json",
        )
        self.job_pop_parser.add_argument(
            "limit_max_steps",
            type=bool,
            required=False,
            default=False,
            help="If True, This worker will not pick up jobs with more steps than the average allowed for that model.",
            location="json",
        )
        self.job_submit_parser.add_argument(
            "seed",
            type=int,
            required=True,
            help="The seed of the generation.",
            location="json",
        )
        self.job_submit_parser.add_argument(
            "censored",
            type=bool,
            required=False,
            default=False,
            help="If true, this image has been censored by the safety filter.",
            location="json",
        )


class ImageModels(v2.Models):
    def __init__(self, api):
        super().__init__(api)
        self.model_job_metadata = api.model(
            "GenerationMetadataStable",
            {
                "type": fields.String(
                    required=True,
                    enum=[
                        "lora",
                        "ti",
                        "censorship",
                        "source_image",
                        "source_mask",
                        "extra_source_images",
                        "batch_index",
                        "information",
                    ],
                    description="The relevance of the metadata field",
                ),
                "value": fields.String(
                    required=True,
                    enum=[
                        "download_failed",
                        "parse_failed",
                        "baseline_mismatch",
                        "csam",
                        "nsfw",
                        "see_ref",
                    ],
                    description="The value of the metadata field",
                ),
                "ref": fields.String(
                    required=False,
                    description="Optionally a reference for the metadata (e.g. a lora ID)",
                    max_length=255,
                ),
            },
        )
        self.response_model_generation_result = api.inherit(
            "GenerationStable",
            self.response_model_generation_result,
            {
                "img": fields.String(
                    title="Generated Image",
                    description="The generated image as a Base64-encoded .webp file.",
                ),
                "seed": fields.String(
                    title="Generation Seed",
                    description="The seed which generated this image.",
                ),
                "id": fields.String(title="Generation ID", description="The ID for this image."),
                "censored": fields.Boolean(
                    description="When true this image has been censored by the worker's safety filter.",
                ),
                "gen_metadata": fields.List(fields.Nested(self.model_job_metadata, skip_none=True)),
            },
        )
        self.response_model_wp_status_full = api.inherit(
            "RequestStatusStable",
            self.response_model_wp_status_lite,
            {
                "generations": fields.List(fields.Nested(self.response_model_generation_result)),
                "shared": fields.Boolean(description="If True, These images have been shared with LAION."),
            },
        )
        self.input_model_loras = api.model(
            "ModelPayloadLorasStable",
            {
                "name": fields.String(
                    required=True,
                    example="Magnagothica",
                    description=(
                        "The exact name or CivitAI Model Page ID of the LoRa. "
                        "If is_version is true, this should be the CivitAI version ID."
                    ),
                    unique=True,
                    min_length=1,
                    max_length=255,
                ),
                "model": fields.Float(
                    required=False,
                    default=1.0,
                    min=-5.0,
                    max=5.0,
                    description="The strength of the LoRa to apply to the SD model.",
                ),
                "clip": fields.Float(
                    required=False,
                    default=1.0,
                    min=-5.0,
                    max=5.0,
                    description="The strength of the LoRa to apply to the clip model.",
                ),
                "inject_trigger": fields.String(
                    required=False,
                    min_length=1,
                    max_length=30,
                    description=(
                        "If set, will try to discover a trigger for this LoRa which matches or is similar to this string "
                        "and inject it into the prompt. "
                        "If 'any' is specified it will be pick the first trigger."
                    ),
                ),
                "is_version": fields.Boolean(
                    required=False,
                    default=False,
                    description=(
                        "If true, will consider the LoRa ID as a CivitAI version ID and search accordingly. "
                        "Ensure the name is an integer."
                    ),
                ),
            },
        )
        self.input_model_tis = api.model(
            "ModelPayloadTextualInversionsStable",
            {
                "name": fields.String(
                    required=True,
                    example="7808",
                    description="The exact name or CivitAI ID of the Textual Inversion.",
                    unique=True,
                    min_length=1,
                    max_length=255,
                ),
                "inject_ti": fields.String(
                    required=False,
                    default=None,
                    enum=["prompt", "negprompt"],
                    description=(
                        "If set, Will automatically add this TI filename to the prompt or negative prompt "
                        "accordingly using the provided strength. "
                        "If this is set to None, then the user will have to manually add the embed to the prompt themselves."
                    ),
                ),
                "strength": fields.Float(
                    required=False,
                    default=1.0,
                    min=-5.0,
                    max=5.0,
                    description="The strength with which to apply the TI to the prompt. Only used when inject_ti is not None",
                ),
            },
        )
        self.input_model_special_payload = api.model("ModelSpecialPayloadStable", {"*": fields.Wildcard(fields.Raw)})
        self.root_model_generation_payload_style_stable = api.model(
            "ModelPayloadStyleStable",
            {
                "sampler_name": fields.String(required=False, default="k_euler_a", enum=list(KNOWN_SAMPLERS)),
                "cfg_scale": fields.Float(required=False, default=7.5, min=0, max=100),
                "denoising_strength": fields.Float(required=False, example=0.75, min=0.01, max=1.0),
                "hires_fix_denoising_strength": fields.Float(required=False, example=0.75, min=0.01, max=1.0),
                "height": fields.Integer(
                    required=False,
                    default=512,
                    description="The height of the image to generate.",
                    min=64,
                    max=3072,
                    multiple=64,
                ),
                "width": fields.Integer(
                    required=False,
                    default=512,
                    description="The width of the image to generate.",
                    min=64,
                    max=3072,
                    multiple=64,
                ),
                "post_processing": fields.List(
                    fields.String(
                        description="The list of post-processors to apply to the image, in the order to be applied.",
                        enum=list(KNOWN_POST_PROCESSORS.keys()),
                    ),
                    unique=True,
                ),
                "karras": fields.Boolean(
                    default=False,
                    description="Set to True to enable karras noise scheduling tweaks.",
                ),
                "tiling": fields.Boolean(
                    default=False,
                    description="Set to True to create images that stitch together seamlessly.",
                ),
                "hires_fix": fields.Boolean(
                    default=False,
                    description=(
                        "Set to True to process the image at base resolution "
                        "before upscaling and re-processing or to use Stable Cascade 2-pass."
                    ),
                ),
                "clip_skip": fields.Integer(
                    required=False,
                    example=1,
                    min=1,
                    max=12,
                    description="The number of CLIP language processor layers to skip.",
                ),
                "facefixer_strength": fields.Float(required=False, example=0.75, min=0, max=1.0),
                "loras": fields.List(fields.Nested(self.input_model_loras, skip_none=True)),
                "tis": fields.List(fields.Nested(self.input_model_tis, skip_none=True)),
                "special": fields.Nested(self.input_model_special_payload, skip_none=True),
                "workflow": fields.String(
                    required=False,
                    default=None,
                    enum=list(KNOWN_WORKFLOWS),
                    description="Explicitly specify the horde-engine workflow to use.",
                ),
                "transparent": fields.Boolean(
                    default=False,
                    description="Set to True to generate the image using Layer Diffuse, creating an image with a transparent background.",
                ),
            },
        )
        # We have to do this to remove the defaults for styles
        temp_model_copy = copy.deepcopy(self.root_model_generation_payload_style_stable)
        v2.remove_all_model_default_params(temp_model_copy)
        self.root_model_generation_payload_style_stable_nodefaults = api.inherit(
            "ModelStyleInputParamsStableNoDefaults",
            temp_model_copy,
        )
        self.root_model_generation_payload_stable = api.inherit(
            "ModelPayloadRootStable",
            self.root_model_generation_payload_style_stable,
            {
                "seed": fields.String(
                    required=False,
                    example="The little seed that could",
                    description="The seed to use to generate this request. You can pass text as well as numbers.",
                ),
                "seed_variation": fields.Integer(
                    required=False,
                    example=1,
                    min=1,
                    max=1000,
                    description="If passed with multiple n, the provided seed will be incremented every time by this value.",
                ),
                "control_type": fields.String(
                    required=False,
                    enum=[
                        "canny",
                        "hed",
                        "depth",
                        "normal",
                        "openpose",
                        "seg",
                        "scribble",
                        "fakescribbles",
                        "hough",
                    ],
                ),
                "image_is_control": fields.Boolean(
                    default=False,
                    description="Set to True if the image submitted is a pre-generated control map for ControlNet use.",
                ),
                "return_control_map": fields.Boolean(
                    default=False,
                    description="Set to True if you want the ControlNet map returned instead of a generated image.",
                ),
                "extra_texts": fields.List(fields.Nested(self.model_extra_texts)),
            },
        )
        # The response for the pop
        self.response_model_generation_payload = api.inherit(
            "ModelPayloadStable",
            self.root_model_generation_payload_stable,
            {
                "prompt": fields.String(
                    description="The prompt which will be sent to Stable Diffusion to generate an image.",
                ),
                "ddim_steps": fields.Integer(default=30),
                "n_iter": fields.Integer(default=1, description="The amount of images to generate."),
                "use_nsfw_censor": fields.Boolean(
                    description="When true will apply NSFW censoring model on the generation.",
                ),
            },
        )
        # The input for the generation
        self.input_model_generation_payload = api.inherit(
            "ModelGenerationInputStable",
            self.root_model_generation_payload_stable,
            {
                "steps": fields.Integer(default=30, required=False, min=1, max=500),
                "n": fields.Integer(
                    default=1,
                    required=False,
                    description="The amount of images to generate.",
                    min=1,
                    max=20,
                ),
            },
        )
        self.response_model_generations_skipped = api.inherit(
            "NoValidRequestFoundStable",
            self.response_model_generations_skipped,
            {
                "max_pixels": fields.Integer(
                    description="How many waiting requests were skipped because they demanded a higher size than this worker provides.",
                ),
                "step_count": fields.Integer(
                    description="How many waiting requests were skipped because they demanded a higher step count that the worker wants.",
                ),
                "unsafe_ip": fields.Integer(
                    description="How many waiting requests were skipped because they came from an unsafe IP.",
                ),
                "img2img": fields.Integer(
                    description="How many waiting requests were skipped because they requested img2img.",
                ),
                "painting": fields.Integer(
                    description="How many waiting requests were skipped because they requested inpainting/outpainting.",
                ),
                "post-processing": fields.Integer(
                    description="How many waiting requests were skipped because they requested post-processing.",
                ),
                "lora": fields.Integer(
                    description="How many waiting requests were skipped because they requested loras.",
                ),
                "controlnet": fields.Integer(
                    description="How many waiting requests were skipped because they requested a controlnet.",
                ),
            },
        )
        self.response_model_job_pop = api.model(
            "GenerationPayloadStable",
            {
                "payload": fields.Nested(self.response_model_generation_payload, skip_none=True),
                "id": fields.String(description="The UUID for this image generation."),
                "ids": fields.List(
                    fields.String(
                        description="The UUID for this image generation.",
                        example="00000000-0000-0000-0000-000000000000",
                    ),
                ),
                "messages": fields.List(fields.Nested(self.response_model_message, skip_none=True)),
                "ttl": fields.Integer(description="The amount of seconds before this job is considered stale and aborted."),
                "skipped": fields.Nested(self.response_model_generations_skipped, skip_none=True),
                "model": fields.String(description="Which of the available models to use for this request."),
                "source_image": fields.String(description="The Base64-encoded webp to use for img2img."),
                "source_processing": fields.String(
                    required=False,
                    default="img2img",
                    enum=["img2img", "inpainting", "outpainting", "remix"],
                    description="If source_image is provided, specifies how to process it.",
                ),
                "source_mask": fields.String(
                    description=(
                        "If img_processing is set to 'inpainting' or 'outpainting', "
                        "this parameter can be optionally provided as the mask of the areas to inpaint. "
                        "If this arg is not passed, the inpainting/outpainting mask has to be embedded as alpha channel."
                    ),
                ),
                "extra_source_images": fields.List(fields.Nested(self.model_extra_source_images)),
                "r2_upload": fields.String(description="The r2 upload link to use to upload this image."),
                "r2_uploads": fields.List(
                    fields.String(description="The r2 upload link to use to upload this image."),
                ),
            },
        )
        self.input_model_job_pop = api.inherit(
            "PopInputStable",
            self.input_model_job_pop,
            {
                "max_pixels": fields.Integer(
                    default=512 * 512,
                    description="The maximum amount of pixels this worker can generate.",
                ),
                "blacklist": fields.List(
                    fields.String(description="Words which, when detected will refuste to pick up any jobs."),
                ),
                "allow_img2img": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up img2img requests.",
                ),
                "allow_painting": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up inpainting/outpainting requests.",
                ),
                "allow_unsafe_ipaddr": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up img2img requests coming from clients with an unsafe IP.",
                ),
                "allow_post_processing": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up requests requesting post-processing.",
                ),
                "allow_controlnet": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up requests requesting ControlNet.",
                ),
                "allow_sdxl_controlnet": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up requests requesting SDXL ControlNet.",
                ),
                "allow_lora": fields.Boolean(
                    default=True,
                    description="If True, this worker will pick up requests requesting LoRas.",
                ),
                "limit_max_steps": fields.Boolean(
                    default=True,
                    description=(
                        "If True, This worker will not pick up jobs with more steps than the average allowed for that model."
                        " this is for use by workers which might run into issues doing too many steps."
                    ),
                ),
            },
        )
        self.input_model_job_submit = api.inherit(
            "SubmitInputStable",
            self.input_model_job_submit,
            {
                "seed": fields.Integer(required=True, description="The seed for this generation."),
                "censored": fields.Boolean(
                    required=False,
                    default=False,
                    description="OBSOLETE (start using meta): If True, this resulting image has been censored.",
                ),
                "gen_metadata": fields.List(fields.Nested(self.model_job_metadata)),
            },
        )
        self.input_model_request_generation = api.model(
            "GenerationInputStable",
            {
                "prompt": fields.String(
                    required=True,
                    description="The prompt which will be sent to Stable Diffusion to generate an image.",
                    min_length=1,
                ),
                "params": fields.Nested(self.input_model_generation_payload, skip_none=True),
                "nsfw": fields.Boolean(
                    default=False,
                    description="Set to true if this request is NSFW. This will skip workers which censor images.",
                ),
                "trusted_workers": fields.Boolean(
                    default=False,
                    description=(
                        "When true, only trusted workers will serve this request. "
                        "When False, Evaluating workers will also be used which can increase speed but adds more risk!"
                    ),
                ),
                "validated_backends": fields.Boolean(
                    default=True,
                    description=(
                        f"When true, only inference backends that are validated by the {horde_title} devs will serve this request. "
                        "When False, non-validated backends will also be used which can increase speed but "
                        "you may end up with unexpected results."
                    ),
                ),
                "slow_workers": fields.Boolean(
                    default=True,
                    description="When True, allows slower workers to pick up this request. Disabling this incurs an extra kudos cost.",
                ),
                "extra_slow_workers": fields.Boolean(
                    default=False,
                    description=(
                        "When True, allows very slower workers to pick up this request. " "Use this when you don't mind waiting a lot."
                    ),
                ),
                "censor_nsfw": fields.Boolean(
                    default=False,
                    description="If the request is SFW, and the worker accidentally generates NSFW, it will send back a censored image.",
                ),
                "workers": fields.List(
                    fields.String(description="Specify up to 5 workers which are allowed to service this request."),
                ),
                "worker_blacklist": fields.Boolean(
                    default=False,
                    required=False,
                    description="If true, the worker list will be treated as a blacklist instead of a whitelist.",
                ),
                "models": fields.List(
                    fields.String(description="Specify which models are allowed to be used for this request."),
                ),
                "source_image": fields.String(
                    required=False,
                    description="The Base64-encoded webp to use for img2img.",
                ),
                "source_processing": fields.String(
                    required=False,
                    default="img2img",
                    enum=["img2img", "inpainting", "outpainting", "remix"],
                    description="If source_image is provided, specifies how to process it.",
                ),
                "source_mask": fields.String(
                    description=(
                        "If source_processing is set to 'inpainting' or 'outpainting', "
                        "this parameter can be optionally provided as the  Base64-encoded webp mask of the areas to inpaint. "
                        "If this arg is not passed, the inpainting/outpainting mask has to be embedded as alpha channel."
                    ),
                ),
                "extra_source_images": fields.List(fields.Nested(self.model_extra_source_images)),
                "r2": fields.Boolean(
                    default=True,
                    description="If True, the image will be sent via cloudflare r2 download link.",
                ),
                "shared": fields.Boolean(
                    default=False,
                    description=(
                        "If True, The image will be shared with LAION for improving their dataset. "
                        "This will also reduce your kudos consumption by 2. For anonymous users, this is always True."
                    ),
                ),
                "replacement_filter": fields.Boolean(
                    default=True,
                    description="If enabled, suspicious prompts are sanitized through a string replacement filter instead.",
                ),
                "dry_run": fields.Boolean(
                    default=False,
                    description="When true, the endpoint will simply return the cost of the request in kudos and exit.",
                ),
                "proxied_account": fields.String(
                    description=(
                        "If using a service account as a proxy, provide this value to identify the actual account "
                        "from which this request is coming from."
                    ),
                ),
                "disable_batching": fields.Boolean(
                    default=False,
                    description=(
                        "When true, This request will not use batching. This will allow you to retrieve accurate seeds. "
                        "Feature is restricted to Trusted users and Patreons."
                    ),
                ),
                "allow_downgrade": fields.Boolean(
                    default=False,
                    description=(
                        "When true and the request requires upfront kudos and the account does not have enough "
                        "The request will be downgraded in steps and resolution so that it does not need upfront kudos."
                    ),
                ),
                "webhook": fields.String(
                    required=False,
                    max_length=1024,
                    min_length=10,
                    example="https://haidra.net/00000000-0000-0000-0000-000000000000",
                    description=(
                        f"Provide a URL where the {horde_title} will send a POST call after each delivered generation. "
                        "The request will include the details of the job as well as the request ID."
                    ),
                ),
                "style": fields.String(
                    required=False,
                    max_length=1024,
                    min_length=3,
                    example="00000000-0000-0000-0000-000000000000",
                    description=("A horde style ID or name to use for this generation"),
                ),
            },
        )
        self.response_model_team_details = api.inherit(
            "TeamDetailsStable",
            self.response_model_team_details,
            {
                "contributions": fields.Float(
                    description="How many megapixelsteps the workers in this team have been rewarded while part of this team.",
                ),
                "performance": fields.Float(
                    description="The average performance of the workers in this team, in megapixelsteps per second.",
                ),
                "speed": fields.Float(
                    description=(
                        "The total expected speed of this team when all workers are working in parallel, " "in megapixelsteps per second."
                    ),
                ),
            },
        )
        # Intentionally left blank to allow to add payloads later
        self.input_model_interrogation_form_payload = api.model(
            "ModelInterrogationFormPayloadStable",
            {"*": fields.Wildcard(fields.String)},
        )
        self.input_model_interrogation_form = api.model(
            "ModelInterrogationFormStable",
            {
                "name": fields.String(
                    required=True,
                    enum=["caption", "interrogation", "nsfw"] + list(KNOWN_POST_PROCESSORS.keys()),
                    description="The type of interrogation this is.",
                    unique=True,
                ),
                "payload": fields.Nested(self.input_model_interrogation_form_payload, skip_none=True),
            },
        )
        self.input_interrogate_request_generation = api.model(
            "ModelInterrogationInputStable",
            {
                "forms": fields.List(fields.Nested(self.input_model_interrogation_form)),
                "source_image": fields.String(
                    required=False,
                    description="The public URL of the image to interrogate.",
                ),
                "slow_workers": fields.Boolean(
                    default=True,
                    description="When True, allows slower workers to pick up this request. Disabling this incurs an extra kudos cost.",
                ),
                "webhook": fields.String(
                    required=False,
                    max_length=1024,
                    min_length=10,
                    example="https://haidra.net/00000000-0000-0000-0000-000000000000",
                    description=(
                        f"Provide a URL where the {horde_title} will send a POST call after each delivered generation. "
                        "The request will include the details of the job as well as the request ID."
                    ),
                ),
            },
        )
        self.response_model_interrogation = api.model(
            "RequestInterrogationResponse",
            {
                "id": fields.String(
                    description="The UUID of the request. Use this to retrieve the request status in the future.",
                ),
                "message": fields.String(
                    default=None,
                    description="Any extra information from the horde about this request.",
                ),
            },
        )
        # Intentionally left blank to allow to add payloads later
        self.response_model_interrogation_form_result = api.model(
            "InterrogationFormResult",
            {"*": fields.Wildcard(fields.Raw)},
        )
        self.response_model_interrogation_form_status = api.model(
            "InterrogationFormStatus",
            {
                "form": fields.String(description="The name of this interrogation form."),
                "state": fields.String(
                    title="Interrogation State",
                    description="The overall status of this interrogation.",
                ),
                "result": fields.Nested(self.response_model_interrogation_form_result, skip_none=True),
            },
        )
        self.response_model_interrogation_status = api.model(
            "InterrogationStatus",
            {
                "state": fields.String(
                    title="Interrogation State",
                    description="The overall status of this interrogation.",
                ),
                "forms": fields.List(fields.Nested(self.response_model_interrogation_form_status, skip_none=True)),
            },
        )
        self.input_model_interrogation_pop = api.model(
            "InterrogationPopInput",
            {
                "name": fields.String(description="The Name of the Worker."),
                "priority_usernames": fields.List(
                    fields.String(description="Users with priority to use this worker."),
                ),
                "forms": fields.List(
                    fields.String(
                        description="The type of interrogation this worker can fulfil.",
                        enum=["caption", "interrogation", "nsfw"] + list(KNOWN_POST_PROCESSORS.keys()),
                        unique=True,
                    ),
                ),
                "amount": fields.Integer(
                    default=1,
                    description="The amount of forms to pop at the same time.",
                ),
                "bridge_agent": fields.String(
                    required=False,
                    default="unknown",
                    example=f"{horde_title} Worker reGen:4.1.0:https://github.com/Haidra-Org/horde-worker-reGen",
                    description="The worker name, version and website.",
                    max_length=1000,
                ),
                "threads": fields.Integer(
                    default=1,
                    description=(
                        "How many threads this worker is running. " "This is used to accurately the current power available in the horde."
                    ),
                    min=1,
                    max=100,
                ),
                "max_tiles": fields.Integer(
                    default=16,
                    description="The maximum amount of 512x512 tiles this worker can post-process.",
                    min=1,
                    max=256,
                ),
            },
        )
        self.response_model_interrogation_pop_payload = api.model(
            "InterrogationPopFormPayload",
            {
                "id": fields.String(
                    description="The UUID of the interrogation form. Use this to post the results in the future.",
                ),
                "form": fields.String(
                    description="The name of this interrogation form",
                    enum=["caption", "interrogation", "nsfw."] + list(KNOWN_POST_PROCESSORS.keys()),
                ),
                "payload": fields.Nested(self.input_model_interrogation_form_payload, skip_none=True),
                "source_image": fields.String(description="The URL From which the source image can be downloaded."),
                "r2_upload": fields.String(description="The URL in which the post-processed image can be uploaded."),
            },
        )
        self.response_model_interrogation_forms_skipped = api.model(
            "NoValidInterrogationsFound",
            {
                "worker_id": fields.Integer(
                    description="How many waiting requests were skipped because they demanded a specific worker.",
                    min=0,
                ),
                "untrusted": fields.Integer(
                    description="How many waiting requests were skipped because they demanded a trusted worker which this worker is not.",
                    min=0,
                ),
                "bridge_version": fields.Integer(
                    example=0,
                    description=(
                        "How many waiting requests were skipped because they require a higher version of the bridge "
                        "than this worker is running (upgrade if you see this in your skipped list)."
                    ),
                    min=0,
                ),
            },
        )
        self.response_model_interrogation_pop = api.model(
            "InterrogationPopPayload",
            {
                "forms": fields.List(fields.Nested(self.response_model_interrogation_pop_payload, skip_none=True)),
                "skipped": fields.Nested(self.response_model_interrogation_forms_skipped, skip_none=True),
            },
        )
        self.response_model_aesthetic_rating = api.model(
            "AestheticRating",
            {
                "id": fields.String(
                    required=True,
                    example="6038971e-f0b0-4fdd-a3bb-148f561f815e",
                    description="The UUID of image being rated.",
                    min_length=36,
                    max_length=36,
                ),
                "rating": fields.Integer(
                    required=True,
                    description="The aesthetic rating 1-10 for this image.",
                    min=1,
                    max=10,
                ),
                "artifacts": fields.Integer(
                    required=False,
                    description=(
                        "The artifacts rating for this image.\n0 for flawless generation that perfectly fits to the prompt.\n"
                        "1 for small, hardly recognizable flaws.\n"
                        "2 small flaws that can easily be spotted, but don not harm the aesthetic experience.\n"
                        "3 for flaws that look obviously wrong, but only mildly harm the aesthetic experience.\n"
                        "4 for flaws that look obviously wrong & significantly harm the aesthetic experience.\n"
                        "5 for flaws that make the image look like total garbage."
                    ),
                    example=1,
                    min=0,
                    max=5,
                ),
            },
        )
        self.input_model_aesthetics_payload = api.model(
            "AestheticsPayload",
            {
                "best": fields.String(
                    required=False,
                    example="6038971e-f0b0-4fdd-a3bb-148f561f815e",
                    description=(
                        "The UUID of the best image in this generation batch (only used when 2+ images generated). "
                        "If 2+ aesthetic ratings are also provided, then they take precedence if they're not tied."
                    ),
                    min_length=36,
                    max_length=36,
                ),
                "ratings": fields.List(
                    fields.Nested(self.response_model_aesthetic_rating, skip_none=True),
                    required=False,
                ),
            },
        )

        self.response_model_single_period_total_img_stat = api.model(
            "SinglePeriodImgStat",
            {
                "images": fields.Integer(description="The amount of images generated during this period."),
                "ps": fields.Integer(description="The amount of pixelsteps generated during this period."),
            },
        )

        self.response_model_stats_img_totals = api.model(
            "StatsImgTotals",
            {
                "minute": fields.Nested(self.response_model_single_period_total_img_stat),
                "hour": fields.Nested(self.response_model_single_period_total_img_stat),
                "day": fields.Nested(self.response_model_single_period_total_img_stat),
                "month": fields.Nested(self.response_model_single_period_total_img_stat),
                "total": fields.Nested(self.response_model_single_period_total_img_stat),
            },
        )

        self.response_model_model_stats = api.model(
            "SinglePeriodImgModelStats",
            {
                "*": fields.Wildcard(
                    fields.Integer(
                        required=True,
                        description="The amount of requests fulfilled for this model.",
                    ),
                ),
            },
        )

        self.response_model_stats_models = api.model(
            "ImgModelStats",
            {
                "day": fields.Nested(self.response_model_model_stats),
                "month": fields.Nested(self.response_model_model_stats),
                "total": fields.Nested(self.response_model_model_stats),
            },
        )

        # Styles
        self.input_model_style_params = api.inherit(
            "ModelStyleInputParamsStable",
            self.root_model_generation_payload_style_stable_nodefaults,
            {
                "steps": fields.Integer(required=False, min=1, max=500),
            },
        )
        self.input_model_style = api.model(
            "ModelStyleInputStable",
            {
                "name": fields.String(
                    required=True,
                    example="My Awesome Image Style",
                    description="The name for the style. Case-sensitive and unique per user.",
                    min_length=1,
                    max_length=100,
                ),
                "info": fields.String(
                    required=False,
                    description="Some information about this style.",
                    example="photorealism excellence.",
                    min_length=10,
                    max_length=1000,
                ),
                "prompt": fields.String(
                    required=False,
                    description=(
                        "The prompt template which will be sent to Stable Diffusion to generate an image. "
                        "The user's prompt will be injected into this."
                        " This argument MUST include a '{p}' which specifies the part where the user's prompt will be injected "
                        "and an '{np}' where the user's negative prompt will be injected (if any)"
                    ),
                    default="{p}{np}",
                    min_length=7,
                ),
                "params": fields.Nested(self.input_model_style_params, skip_none=True),
                "public": fields.Boolean(
                    default=True,
                    description=(
                        "When true this style will be listed among all styles publicly."
                        "When false, information about this style can only be seen by people who know its ID or name."
                    ),
                ),
                "nsfw": fields.Boolean(
                    default=False,
                    description=("When true, it signified this style is expected to generare NSFW images primarily."),
                ),
                "tags": fields.List(
                    fields.String(
                        description="Tags describing this style. Used for filtering and discovery.",
                        min_length=1,
                        max_length=25,
                        example="photorealistic",
                    ),
                ),
                "models": fields.List(
                    fields.String(description="The models to use with this style.", min_length=1, example="stable_diffusion"),
                ),
                "sharedkey": fields.String(
                    required=False,
                    min_length=36,
                    max_length=36,
                    description="The UUID of a shared key which will be used to fulfil this style when active.",
                    example="00000000-0000-0000-0000-000000000000",
                ),
            },
        )
        self.patch_model_style = api.model(
            "ModelStylePatchStable",
            {
                "name": fields.String(
                    required=False,
                    example="My Awesome Image Style",
                    description="The name for the style. Case-sensitive and unique per user.",
                    min_length=1,
                    max_length=100,
                ),
                "info": fields.String(
                    required=False,
                    example="photorealism excellence.",
                    description="Extra information about this style.",
                    min_length=1,
                    max_length=1000,
                ),
                "prompt": fields.String(
                    required=False,
                    description=(
                        "The prompt template which will be sent to Stable Diffusion to generate an image. "
                        "The user's prompt will be injected into this."
                        " This argument MUST include a '{p}' which specifies the part where the user's prompt will be injected "
                        "and an '{np}' where the user's negative prompt will be injected (if any)"
                    ),
                    min_length=7,
                ),
                "params": fields.Nested(self.input_model_style_params, skip_none=True),
                "public": fields.Boolean(
                    default=True,
                    description=(
                        "When true this style will be listed among all styles publicly."
                        "When false, information about this style can only be seen by people who know its ID or name."
                    ),
                ),
                "nsfw": fields.Boolean(
                    default=False,
                    description=("When true, it signified this style is expected to generare NSFW images primarily."),
                ),
                "tags": fields.List(
                    fields.String(
                        description="Tags describing this style. Used for filtering and discovery.",
                        min_length=1,
                        max_length=25,
                        example="photorealistic",
                    ),
                ),
                "models": fields.List(
                    fields.String(description="The models to use with this style.", min_length=1, example="stable_diffusion"),
                ),
                "sharedkey": fields.String(
                    required=False,
                    min_length=36,
                    max_length=36,
                    description="The UUID of a shared key which will be used to fulfil this style when active.",
                    example="00000000-0000-0000-0000-000000000000",
                ),
            },
        )
        self.input_model_style_example_post = api.model(
            "InputStyleExamplePost",
            {
                "url": fields.String(
                    example="https://lemmy.dbzer0.com/pictrs/image/c9915186-ca30-4f5a-873c-a91287fb4419.webp",
                    required=True,
                    description="Any extra information from the horde about this request.",
                ),
                "primary": fields.Boolean(
                    required=True,
                    default=False,
                    description="When true this image is to be used as the primary example for this style.",
                ),
            },
        )
        self.input_model_style_example_patch = api.model(
            "InputStyleExamplePost",
            {
                "url": fields.String(
                    example="https://lemmy.dbzer0.com/pictrs/image/c9915186-ca30-4f5a-873c-a91287fb4419.webp",
                    required=False,
                    description="Any extra information from the horde about this request.",
                ),
                "primary": fields.Boolean(
                    required=False,
                    description="When true this image is to be used as the primary example for this style.",
                ),
            },
        )
        self.response_model_style_example = api.inherit(
            "StyleExample",
            self.input_model_style_example_post,
            {
                "id": fields.String(
                    example="00000000-0000-0000-0000-000000000000",
                    description="The UUID of this example.",
                ),
            },
        )

        self.response_model_style = api.inherit(
            "StyleStable",
            self.input_model_style,
            {
                "id": fields.String(
                    description="The UUID of the style. Use this to use the style or retrieve its information in the future.",
                    min_length=36,
                    max_length=36,
                    example="00000000-0000-0000-0000-000000000000",
                ),
                "use_count": fields.Integer(description="The amount of times this style has been used in generations."),
                "creator": fields.String(description="The alias of the user to whom this style belongs to.", example="db0#1"),
                "examples": fields.List(fields.Nested(self.response_model_style_example, skip_none=True)),
                "shared_key": fields.Nested(self.response_model_sharedkey_details, skip_none=True),
            },
        )
