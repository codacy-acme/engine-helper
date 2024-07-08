# Codacy to Semgrep Config Converter

This Python script generates a Semgrep configuration file from Codacy's API. It allows users to select a specific coding standard, tool, and languages to create a customized Semgrep configuration based on Codacy's enabled patterns.

## Features

- Fetches coding standards from a specified Codacy organization
- Retrieves tools associated with a selected coding standard
- Gathers code patterns for a chosen tool (default: Semgrep)
- Filters enabled patterns and organizes them by language
- Generates a Semgrep-compatible YAML configuration file

## Prerequisites

- Python 3.6+
- Codacy API Token

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/codacy-semgrep-config-converter.git
   cd codacy-semgrep-config-converter
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Set your Codacy API token as an environment variable:

```
export CODACY_API_TOKEN=your_codacy_api_token_here
```

## Usage

Run the script with the following command:

```
python codacy_to_semgrep.py [--organization ORGANIZATION] [--tool TOOL_UUID]
```

Arguments:
- `--organization`: (Optional) Specify the Codacy organization name
- `--tool`: (Optional) Specify a different tool UUID (default is Semgrep's UUID)

If you don't provide the organization name as an argument, you'll be prompted to enter it during script execution.

## Script Workflow

1. Fetch coding standards for the specified organization
2. Prompt user to select a coding standard
3. Retrieve tools associated with the selected coding standard
4. Fetch code patterns for the selected tool (default: Semgrep)
5. Filter enabled patterns
6. Display available languages and prompt user to select desired languages
7. Generate Semgrep configuration based on selected patterns and languages
8. Save the configuration to `semgrep_config.yaml`
9. Display a summary of rules added per language

## Output

The script generates a `semgrep_config.yaml` file in the current directory. This file can be used directly with Semgrep for code analysis.  You will need to rename this file to `.semgrep.yaml` and place it in the root of your repository.

## Error Handling

The script includes error handling for common issues such as:
- Missing Codacy API token
- API request failures
- Invalid user inputs

If an error occurs, an informative message will be displayed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

