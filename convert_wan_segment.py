import os
import re
import yaml

def convert_wan_segment_to_string(directory):
    """
    Converts the 'segment' parameter of WAN networks from a list to a string in YAML files and removes '#Revert to Array' comments.
    """
    for filename in os.listdir(directory):
        if filename.endswith((".yaml", ".yml")):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    data = yaml.safe_load(content)

                if data and isinstance(data, dict):
                    for service_type, services in data.items():
                        if service_type == 'seaf.ta.services.network':
                            for network_name, network_data in services.items():
                                if network_data.get('type') == 'WAN':
                                    if isinstance(network_data.get('segment'), list):
                                        # Convert the segment list to a string (first element)
                                        network_data['segment'] = network_data['segment'][0]
                                    # Remove the '#Revert to Array' comment
                                    if '#Revert to Array' in network_data:
                                        del network_data['#Revert to Array']

                # Write the modified data back to the file
                with open(filepath, 'w', encoding='utf-8') as file:
                    yaml.dump(data, file, indent=2, allow_unicode=True)

                print(f"Processed file: {filename}")

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

if __name__ == "__main__":
    directory_path = "seaf-dzo-example/architecture/ta/seafexample"
    convert_wan_segment_to_string(directory_path)