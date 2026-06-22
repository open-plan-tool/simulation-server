const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileListEl = document.getElementById('file-list');
const submitBtn = document.getElementById('submit-btn');

const mosaikDropZone = document.getElementById('mosaik-drop-zone');
const mosaikFileInput = document.getElementById('mosaik-file-input');
const mosaikFileListEl = document.getElementById('mosaik-file-list');
const submitMosaikBtn = document.getElementById('submit-mosaik-btn');

let selectedFiles = [];
let selectedMosaikFile = null;

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tab);
    });
    document.getElementById('daceds-card').classList.toggle('hidden', tab !== 'daceds');
    document.getElementById('mosaik-card').classList.toggle('hidden', tab !== 'mosaik');
}

// --- DaceDS Drag & Drop ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    addFiles(e.dataTransfer.files);
});

fileInput.addEventListener('change', () => {
    addFiles(fileInput.files);
    fileInput.value = '';
});

function addFiles(fileListObj) {
    for (const f of fileListObj) {
        if (!selectedFiles.find(s => s.name === f.name && s.size === f.size)) {
            selectedFiles.push(f);
        }
    }
    renderFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderFileList() {
    fileListEl.innerHTML = selectedFiles.map((f, i) =>
        `<li>
            <span class="name">${f.name}</span>
            <span class="size">${formatSize(f.size)}</span>
            <button class="remove" onclick="removeFile(${i})">✕</button>
        </li>`
    ).join('');
    submitBtn.disabled = selectedFiles.length === 0;
}

// --- Mosaik Drag & Drop ---
mosaikDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    mosaikDropZone.classList.add('dragover');
});

mosaikDropZone.addEventListener('dragleave', () => {
    mosaikDropZone.classList.remove('dragover');
});

mosaikDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    mosaikDropZone.classList.remove('dragover');
    handleMosaikFiles(e.dataTransfer.files);
});

mosaikFileInput.addEventListener('change', () => {
    handleMosaikFiles(mosaikFileInput.files);
    mosaikFileInput.value = '';
});

function handleMosaikFiles(fileListObj) {
    if (fileListObj.length > 0) {
        selectedMosaikFile = fileListObj[0];
        renderMosaikFileList();
    }
}

function removeMosaikFile() {
    selectedMosaikFile = null;
    renderMosaikFileList();
}

function renderMosaikFileList() {
    if (selectedMosaikFile) {
        mosaikFileListEl.innerHTML =
            `<li>
                <span class="name">${selectedMosaikFile.name}</span>
                <span class="size">${formatSize(selectedMosaikFile.size)}</span>
                <button class="remove" onclick="removeMosaikFile()">✕</button>
            </li>`;
        submitMosaikBtn.disabled = false;
    } else {
        mosaikFileListEl.innerHTML = '';
        submitMosaikBtn.disabled = true;
    }
}

// --- Submit ---
async function submitDaceDS() {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append('files', f));

    try {
        const res = await fetch('/submit', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            alert('Error: ' + (data.error || 'Submission failed'));
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Simulation';
            return;
        }

        const taskId = data.task_id;
        document.getElementById('daceds-status-card').classList.remove('hidden');
        document.getElementById('daceds-task-id-display').textContent = 'Task ID: ' + taskId;
        setStatus('pending', 'Queued — waiting for a worker...', 'daceds');

        const poll = setInterval(async () => {
            const check = await fetch('/check/' + taskId);
            const status = await check.json();

            if (status.status === 'RUNNING') {
                setStatus('running', 'Simulation is running...', 'daceds');
            } else if (status.status === 'DONE') {
                clearInterval(poll);
                setStatus('done', 'Simulation complete!', 'daceds');
                showResults(taskId, status.downloads || [], 'daceds');
            } else if (status.status === 'ERROR') {
                clearInterval(poll);
                setStatus('error', 'Error: ' + (status.error || 'Unknown error'), 'daceds');
            }
        }, 2000);

    } catch (err) {
        alert('Network error: ' + err.message);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Simulation';
    }
}

async function submitMosaik() {
    submitMosaikBtn.disabled = true;
    submitMosaikBtn.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('file', selectedMosaikFile);

    try {
        const res = await fetch('/submit_mosaik', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            alert('Error: ' + (data.error || 'Submission failed'));
            submitMosaikBtn.disabled = false;
            submitMosaikBtn.textContent = 'Submit Mosaik Simulation';
            return;
        }

        const taskId = data.task_id;
        document.getElementById('mosaik-status-card').classList.remove('hidden');
        document.getElementById('mosaik-task-id-display').textContent = 'Task ID: ' + taskId;
        setStatus('pending', 'Queued — waiting for a worker...', 'mosaik');

        const poll = setInterval(async () => {
            const check = await fetch('/check/' + taskId);
            const status = await check.json();

            if (status.status === 'RUNNING') {
                setStatus('running', 'Simulation is running...', 'mosaik');
            } else if (status.status === 'DONE') {
                clearInterval(poll);
                setStatus('done', 'Simulation complete!', 'mosaik');
                showResults(taskId, status.downloads || [], 'mosaik');
            } else if (status.status === 'ERROR') {
                clearInterval(poll);
                setStatus('error', 'Error: ' + (status.error || 'Unknown error'), 'mosaik');
            }
        }, 2000);

    } catch (err) {
        alert('Network error: ' + err.message);
        submitMosaikBtn.disabled = false;
        submitMosaikBtn.textContent = 'Submit Mosaik Simulation';
    }
}

function setStatus(type, message, tab) {
    const bar = document.getElementById(tab + '-status-bar');
    bar.className = 'status-bar ' + type;
    document.getElementById(tab + '-status-text').textContent = message;
    document.getElementById(tab + '-status-spinner').style.display =
        (type === 'done' || type === 'error') ? 'none' : 'block';
}

function showResults(taskId, downloads, tab) {
    const resultsCard = document.getElementById(tab + '-results-card');
    const resultsList = document.getElementById(tab + '-results-list');
    resultsCard.classList.remove('hidden');

    if (downloads.length === 0) {
        resultsList.innerHTML = '<li>No result files found.</li>';
        return;
    }

    resultsList.innerHTML = downloads.map(url => {
        const filename = url.split('/').pop();
        return `<li><a href="${url}" download>${filename}</a></li>`;
    }).join('');
}

function resetForm(tab) {
    if (tab === 'daceds') {
        selectedFiles = [];
        renderFileList();
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submit Simulation';
        document.getElementById('daceds-status-card').classList.add('hidden');
        document.getElementById('daceds-results-card').classList.add('hidden');
    } else if (tab === 'mosaik') {
        selectedMosaikFile = null;
        renderMosaikFileList();
        submitMosaikBtn.disabled = true;
        submitMosaikBtn.textContent = 'Submit Mosaik Simulation';
        document.getElementById('mosaik-status-card').classList.add('hidden');
        document.getElementById('mosaik-results-card').classList.add('hidden');
    }
}