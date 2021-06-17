# engine-helper

An helper to enable, disable or choose to use or not configuration files for Codacy engines


## Usage

Create a file named auth.cookie and dump inside it the value of your codacy cookie

The requirements.txt list all Python libraries that should be installed before executing.

    pip install -r requirements.txt

arguments:
    -h, --help            show this help message and exit
    --token TOKEN         the api-token to be used on the REST API
    --action {enableengine,disableengine,listengines,useconfigurationfile,dontuseconfigurationfile} action to take
    --which WHICH         repository to be updated, none means all
    --provider PROVIDER   git provider
    --organization ORGANIZATION   organization id
    --engine ENGINE       engine id
    --baseurl BASEURL     codacy server address (ignore if cloud)