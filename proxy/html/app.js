async function loadData() {
    const statusBox = document.getElementById("status");

    try {
        const response = await fetch("/api/");
        const data = await response.json();

        statusBox.textContent = JSON.stringify(data, null, 2);

    } catch (err) {
        statusBox.textContent = "Error connecting to API: " + err;
    }
}

window.onload = loadData;