// js/main.js
let pyodide;
let editorOld, editorNew;

async function loadPyodideAndScript() {
    pyodide = await loadPyodide();
    const pythonCode = await fetch("convert.py").then(res => res.text());
    await pyodide.runPythonAsync(pythonCode);
}

async function runPythonConversion() {
    const xmlInput = editorOld.getValue();
    const selectedVersion = document.getElementById("odooVersion").value;

    pyodide.globals.set("input_xml", xmlInput);

    const pyFunc = selectedVersion === "18" ? "convert_xml_odoo18" : "convert_xml_odoo17";
    const result = await pyodide.runPythonAsync(`${pyFunc}(input_xml)`);

    editorNew.setValue(result);
}

// Gắn vào window để HTML gọi được
window.runPythonConversion = runPythonConversion;

loadPyodideAndScript();

window.onload = function () {
    editorOld = CodeMirror.fromTextArea(document.getElementById("oldXml"), {
        mode: "xml",
        theme: "monokai",
        lineNumbers: true,
        lineWrapping: true
    });

    editorNew = CodeMirror.fromTextArea(document.getElementById("newXml"), {
        mode: "xml",
        theme: "monokai",
        lineNumbers: true,
        lineWrapping: true,
        readOnly: true
    });
};

// Copy to clipboard functionality
document.addEventListener("DOMContentLoaded", () => {
    const copyBtn = document.getElementById("copyBtn");
    const copyStatus = document.getElementById("copyStatus");

    copyBtn.addEventListener("click", () => {
        const text = editorNew.getValue();
        navigator.clipboard.writeText(text).then(() => {
            copyStatus.innerText = "Copied ✅";
            setTimeout(() => {
                copyStatus.innerText = "";
            }, 1500);
        }).catch(() => {
            copyStatus.innerText = "Failed to copy ❌";
        });
    });
});
