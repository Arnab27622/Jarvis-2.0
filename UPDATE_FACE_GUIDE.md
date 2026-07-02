# How to Update Your Jarvis Face Authentication Image

Jarvis 2.0 uses a highly secure caching mechanism for facial recognition. When Jarvis scans your face for the first time, it extracts your unique biometric features (encodings) and stores them in a secure, binary file (`owner_encoding.npy`). 

Because JARVIS reads directly from this binary file to verify your identity, **simply replacing the `owner.jpg` file is no longer enough to update your face**.

Follow these exact steps if you want JARVIS to recognize a new face or an updated image:

## Step 1: Add the New Image
1. Place your new clear, front-facing image inside the `data/images/` directory.
2. Rename the new image exactly to `owner.jpg` (replace the old one if it's still there).

## Step 2: Delete the Old Encodings
1. Open the `data/images/` directory.
2. Find the file named `owner_encoding.npy` and **delete it**.

## Step 3: Restart Jarvis
1. Start Jarvis 2.0 normally.
2. Because you deleted `owner_encoding.npy`, JARVIS will automatically detect the missing encodings.
3. It will read your newly provided `owner.jpg`, generate the new secure biometric encodings, and recreate `owner_encoding.npy` automatically for all future authentications.

> **Security Note:** This setup prevents a malicious user from simply dropping a new photo into the images folder to bypass your facial recognition lock!
