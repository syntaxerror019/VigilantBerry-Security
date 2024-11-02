document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.nav-tabs a');
    const contents = document.querySelectorAll('.tab-content');
    const hamburger = document.querySelector('.hamburger');
    const sidebar = document.querySelector('.sidebar');

    const closeBtn = document.getElementById('closeBtn');
    const notification = document.getElementById('notification');
    const notificationText = notification.querySelector('span'); // Select the span inside notification

    closeBtn.addEventListener('click', () => {
        notification.classList.remove('show');
        notification.classList.add('hidden');
    });

    document.querySelectorAll('.cameraForm').forEach(function(form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent the default form submission
            form.submit();

            spinner_overlay("Saving your settings...");

            const checkAlive = setInterval(() => {
                if (isAlive()) {
                    clearInterval(checkAlive);
                    setTimeout(() => {
                        close_overlay();
                        window.location.reload(); //get new data
                    }, 3000);
                }
            }, 1000);
        });
    });

    window.addEventListener('hashchange', function() {

        // activate the first tab by default
        tabs[0].classList.add('active');
        contents[0].classList.add('active');

        const hash = window.location.hash;

        if (hash) {
            const targetTab = document.querySelector(`.nav-tabs a[href="${hash}"]`);
            if (targetTab) {
                tabs.forEach(tab => tab.classList.remove('active'));
                targetTab.classList.add('active');

                contents.forEach(content => content.classList.remove('active'));
                document.querySelector(hash).classList.add('active');
            }
        }
    });

    // Trigger the event listener on page load to handle the initial URL hash
    window.dispatchEvent(new Event('hashchange'));

    tabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            contents.forEach(content => content.classList.remove('active'));
            document.querySelector(this.getAttribute('href')).classList.add('active');

            // Close sidebar on mobile after selecting a tab
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
            }
        });
    });

    hamburger.addEventListener('click', function() {
        sidebar.classList.toggle('open');
    });

});

function isAlive() {
    return fetch('/alive')
        .then(response => response.status === 200)
        .catch(() => false);
};

function spinner_overlay(text) {
    document.getElementById("spinner-text").textContent = text;
    document.getElementById("spinner-overlay").style.display = "flex";
}

function close_overlay() {
    document.getElementById("spinner-overlay").style.display = "none";
}

function notify(text, header, type = 'alert-info') {
    const notification = document.getElementsByClassName("notification")[0];
    const message = notification.querySelector('span');

    if (type === 'alert-danger') {
        text = `⛔ ${text}`;
    }
    else if (type === 'alert-warning') {
        text = `⚠️ ${text}`;
    }
    else if (type === 'alert-success') {
        text = `✅ ${text}`;
    }
    else {
        text = `ℹ️ ${text}`;
    }

    message.textContent = text;

    notification.classList.remove('hidden');
    notification.classList.add('show');
}

function finish() {
    // send request back to server about which cameras to use:
    const path = document.querySelector('#storage-path').value;
    const checkboxes = document.querySelectorAll('.camera-checkbox');
    const selectedCameras = [];
    checkboxes.forEach(camera => {
        console.log(camera.value, camera.checked);
        if (camera.checked) {
            selectedCameras.push(camera.value);
        }
    });

    if (selectedCameras.length === 0) {
        alert('Please select at least one camera to proceed.');
        return;
    }

    // send request to server
    fetch('/camera_selection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({cameras: selectedCameras, path: path})
    });

    const checkAlive = setInterval(() => {
        if (isAlive()) {
            clearInterval(checkAlive);
            close_overlay();
        } else {
            spinner_overlay("Saving your settings...");
        }
    }, 2000);
}

function next(currentId, upcomingId) {
    const current = document.getElementById(currentId);
    const upcoming = document.getElementById(upcomingId);

    current.classList.add('hidden');
    upcoming.classList.remove('hidden');
}

function check_path() {
    const path = document.querySelector('#storage-path').value;
    if (path === '') {
        finish();
        return;
    }
    fetch('/footage_location', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({path: path})
    })
    .then(response => response.json())
    .then(data => {
        console.log('Response code:', data.code);
        console.log('Response message:', data.message);

        if (data.code === 200) {
            finish();
        } else {
            notify(data.message, 'error', 'alert-danger');
        }
    })
    .catch(error => {
        // Handle any errors that occurred during the request
        console.error('Error:', error);
        notify('An error occurred while, please try again later.', "Error", "alert-danger");
    });
}