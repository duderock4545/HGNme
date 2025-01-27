import face_recognition
import os
import pickle

# Directory containing images for training
image_dir = r'/home/checkout/Documents/hgn/recon/ddotvid/photos'  # Update this to the correct directory
output_pkl = 'train.pkl'  # Output file for encodings

Encodings = []  # List to store face encodings
Names = []  # List to store corresponding names

# Iterate through all images in the directory
for root, dirs, files in os.walk(image_dir):
    for file in files:
        # Skip non-image files
        if not (file.endswith(".jpg") or file.endswith(".png")):
            continue

        # Extract the name (e.g., william_1 -> william)
        name = file.split("_")[0]  # Extract everything before the underscore
        path = os.path.join(root, file)

        # Load the image and compute the encoding
        print(f"Processing: {path}")
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)

        # Skip if no face is detected
        if not encodings:
            print(f"No face found in {path}. Skipping.")
            continue

        # Add the encoding and name
        Encodings.append(encodings[0])
        Names.append(name)

# Save encodings and names to a pickle file
with open(output_pkl, 'wb') as f:
    pickle.dump(Names, f)
    pickle.dump(Encodings, f)

print("Training completed. Encodings saved to:", output_pkl)



