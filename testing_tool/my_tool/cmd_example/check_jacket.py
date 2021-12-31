from google.cloud import vision # google-cloud-vision==1.0.0
import io

def is_jacket(image_path):
    """Detects labels in the file."""
    client = vision.ImageAnnotatorClient()

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.label_detection(image=image)
    labels = response.label_annotations

    lst = []
    for label in labels:
        lst.append(label.description)

    if "jacket" in lst:
        return True
    else:
        return False

if __name__ == '__main__':
    is_jacket("jacket.png")