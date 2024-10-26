# VigilantBerry - CCTV System for RPi 📹

Welcome to **VigilantBerry**, the ultimate homebrew security camera system designed to run seamlessly on your Raspberry Pi! With its powerful features and customizable settings, VigilantBerry transforms your Raspberry Pi into a smart security solution that keeps your home safe and secure. 

## Features 🌟

### 1. Motion Detection and Tracking 🚶‍♂️👁️
VigilantBerry utilizes advanced algorithms to detect movement in your designated monitoring areas. When motion is detected, the system can trigger recording or send alerts, ensuring you never miss a moment. The tracking feature enables the camera to follow movement within its field of view, providing comprehensive surveillance.

### 2. Multiple Camera Support 🎥🎥🎥
Whether you want to monitor your living room, backyard, or garage, VigilantBerry supports multiple camera setups. Connect several cameras to your Raspberry Pi, and keep an eye on every corner of your home. Each camera can be configured individually, giving you complete control over your security system.

### 3. Static Pictures 📸
In addition to video recording, VigilantBerry allows you to capture static images at specified intervals or upon detecting motion. These snapshots are perfect for creating a timeline of events and can be stored for later review.

### 4. 24/7 Recording ⏰
Never worry about missing crucial moments! With 24/7 recording capabilities, VigilantBerry continuously captures video footage, ensuring you have a complete record of events. Customize your recording schedule to suit your needs, whether it's all day or only during specific hours.

### 5. Customizable Settings ⚙️
VigilantBerry offers a wide range of customizable settings, allowing you to tailor the system to your specific requirements. Adjust motion sensitivity, recording duration, and notification preferences to create a setup that works best for you.

### 6. Adjustable Auto-Deletion 🗑️
Manage your storage space effortlessly with VigilantBerry's adjustable auto-deletion feature. Set parameters to automatically delete older recordings after a specified time, ensuring your system remains efficient and that you always have the latest footage on hand.

### 7. Easy Configuration 📊
Configuring VigilantBerry is a breeze! With a user-friendly interface, you can set up your cameras, customize settings, and monitor your footage with minimal hassle. Enjoy a hassle-free experience without compromising on functionality.

## Getting Started 🚀

VigilantBerry is designed to be straightforward and user-friendly. Whether you're a beginner or an experienced tech enthusiast, you'll find it easy to set up and start using.

### Installation
To begin, run the following commands to clone the repository:
```bash
git clone https://github.com/syntaxerror019/VigilantBerry
cd VigilantBerry
```

To install, you may use the interactive installation script.
```bash
sudo ./installer.sh
```
If you are wary about running an elevated shell script, you may inspect the contents for your self.
This whole project, including the installer is open source. Everything is in the repository.
<br><br>
If you see an error or suspect something has gone wrong, it is wise to inspect the `log.txt` file.
Here you will find a full history of the installation process.
<br>
If you need assistance, please send an email to sntx@sntx.dev or fill out <a href="https://report.sntx.dev/error?url=(not%20applicable)&code=(not%20applicable)">this form</a>

### First-run
To run the software, you must first navigate to the cloned repository folder.
Run the following to start the venv and run the python script:
```bash
./vigiberry.sh
```
This will start a webserver at the shown URL. Navigate to the URL in a web browser.
You will be prompted to fill out the setup page. This is only necessary once.

### Future Features 🌈
Future updates may include:
- Integration with smart home systems 🏠
- Auto updating features for software
- Cloud storage options ☁️

## Contributing 🤝
We welcome contributions from the community! If you'd like to enhance VigilantBerry with new features or improvements, please feel free to open issues, suggest features, or submit pull requests. Together, we can make VigilantBerry even better!

## License 📝
This project is licensed under the MIT License.

## Support 🙌
If you have any questions or need assistance, feel free to open an issue in this repository. We’re here to help!

---

Thank you for checking out **VigilantBerry**! We hope you enjoy using it as much as we enjoyed building it. Stay vigilant and secure! 🔒✨
