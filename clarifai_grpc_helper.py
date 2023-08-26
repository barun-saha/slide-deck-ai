from global_config import GlobalConfig

######################################################################################################
# In this section, we set the user authentication, user and app ID, model details, and the URL of
# the text we want as an input. Change these strings to run your own example.
######################################################################################################

# Your PAT (Personal Access Token) can be found in the portal under Authentification
PAT = '7244fc3df026429d819f9df31309ab9d'
# Specify the correct user_id/app_id pairings
# Since you're making inferences outside your app's scope
USER_ID = 'meta'
APP_ID = 'Llama-2'
# Change these to whatever model and text URL you want to use
MODEL_ID = 'llama2-13b-chat'
MODEL_VERSION_ID = '79a1af31aa8249a99602fc05687e8f40'
TEXT_FILE_URL = 'https://samples.clarifai.com/negative_sentence_12.txt'

############################################################################
# YOU DO NOT NEED TO CHANGE ANYTHING BELOW THIS LINE TO RUN THIS EXAMPLE
############################################################################

from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

channel = ClarifaiChannel.get_grpc_channel()
stub = service_pb2_grpc.V2Stub(channel)

metadata = (
    ('authorization', 'Key ' + GlobalConfig.CLARIFAI_PAT),
    # ('temp', '0.9'),  # Does not work
)

userDataObject = resources_pb2.UserAppIDSet(
    user_id=GlobalConfig.CLARIFAI_USER_ID,
    app_id=GlobalConfig.CLARIFAI_APP_ID
)

RAW_TEXT = '''You are a helpful, intelligent chatbot. 
Create the slides for a presentation on the given topic. 
Include main headings for each slide, detailed bullet points for each slide. 
Add relevant content to each slide.
The output should be complete, coherent, and have maximum 255 tokens.

Topic:
Talk about AI, covering what it is and how it works. Add its pros, cons, and future prospects. Also, cover its job prospects.
'''

post_model_outputs_response = stub.PostModelOutputs(
    service_pb2.PostModelOutputsRequest(
        user_app_id=userDataObject,  # The userDataObject is created in the overview and is required when using a PAT
        model_id=GlobalConfig.CLARIFAI_MODEL_ID,
        # version_id=MODEL_VERSION_ID,  # This is optional. Defaults to the latest model version
        inputs=[
            resources_pb2.Input(
                data=resources_pb2.Data(
                    text=resources_pb2.Text(
                        # url=TEXT_FILE_URL,
                        raw=RAW_TEXT
                    )
                )
            )
        ]
    ),
    metadata=metadata
)
if post_model_outputs_response.status.code != status_code_pb2.SUCCESS:
    print(post_model_outputs_response.status)
    raise Exception(f"Post model outputs failed, status: {post_model_outputs_response.status.description}")

# Since we have one input, one output will exist here
output = post_model_outputs_response.outputs[0]

print("Completion:\n")
print(output.data.text.raw)
