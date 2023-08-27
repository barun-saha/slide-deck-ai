from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

from global_config import GlobalConfig


CHANNEL = ClarifaiChannel.get_grpc_channel()
STUB = service_pb2_grpc.V2Stub(CHANNEL)

METADATA = (
    ('authorization', 'Key ' + GlobalConfig.CLARIFAI_PAT),
)

USER_DATA_OBJECT = resources_pb2.UserAppIDSet(
    user_id=GlobalConfig.CLARIFAI_USER_ID,
    app_id=GlobalConfig.CLARIFAI_APP_ID
)

RAW_TEXT = '''You are a helpful, intelligent chatbot. Create the slides for a presentation on the given topic. Include main headings for each slide, detailed bullet points for each slide. Add relevant content to each slide. Do not output any blank line.

Topic:
Talk about AI, covering what it is and how it works. Add its pros, cons, and future prospects. Also, cover its job prospects.
'''


def get_text_from_llm(prompt: str) -> str:
    post_model_outputs_response = STUB.PostModelOutputs(
        service_pb2.PostModelOutputsRequest(
            user_app_id=USER_DATA_OBJECT,  # The userDataObject is created in the overview and is required when using a PAT
            model_id=GlobalConfig.CLARIFAI_MODEL_ID,
            # version_id=MODEL_VERSION_ID,  # This is optional. Defaults to the latest model version
            inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(
                        text=resources_pb2.Text(
                            raw=prompt
                        )
                    )
                )
            ]
        ),
        metadata=METADATA
    )

    if post_model_outputs_response.status.code != status_code_pb2.SUCCESS:
        print(post_model_outputs_response.status)
        raise Exception(f"Post model outputs failed, status: {post_model_outputs_response.status.description}")

    # Since we have one input, one output will exist here
    output = post_model_outputs_response.outputs[0]

    # print("Completion:\n")
    # print(output.data.text.raw)

    return output.data.text.raw


if __name__ == '__main__':
    topic = ('Talk about AI, covering what it is and how it works.'
             ' Add its pros, cons, and future prospects.'
             ' Also, cover its job prospects.'
             )
    print(topic)

    with open(GlobalConfig.SLIDES_TEMPLATE_FILE, 'r') as in_file:
        prompt_txt = in_file.read()
        prompt_txt = prompt_txt.replace('{topic}', topic)
        response_txt = get_text_from_llm(prompt_txt)

        print('Output:\n', response_txt)
