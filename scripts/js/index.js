// ************************ Drag and drop ***************** //
// Original code from https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
// modified slightly to fit my needs. 
let dropArea = document.getElementById("drop-area")
const canvas = document.getElementById('canvas');
// const image = document.getElementById('selected-image')
const image = document.createElement("img");
// Prevent default drag behaviors
;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, preventDefaults, false)   
  document.body.addEventListener(eventName, preventDefaults, false)
})

// Highlight drop area when item is dragged over it
;['dragenter', 'dragover'].forEach(eventName => {
  dropArea.addEventListener(eventName, highlight, false)
})

;['dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, unhighlight, false)
})

// Handle dropped files
dropArea.addEventListener('drop', handleDrop, false)

function preventDefaults (e) {
  e.preventDefault()
  e.stopPropagation()
}

function highlight(e) {
  dropArea.classList.add('highlight')
}

function unhighlight(e) {
  dropArea.classList.remove('active')
}

dropArea.addEventListener('drop', handleDrop, false)

function handleDrop(e) {
  let dt = e.dataTransfer
  let files = dt.files
  ParseFiles(files)

}

function ParseFiles(files){
    console.log(files)
    const file = files[0];
    console.log("file" + file)
    const imageType = /image.*/;
    console.log("img type" + imageType)
    if (file.type.match(imageType)) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onloadend = () => {
        image.src = reader.result;
        let img_url = reader.result
        let img_base64 = img_url.replace("data:image/png;base64,","");
        // send the img to server
        communicate(img_base64);
        }
      
    }
    else {
      alert("Please drop image file, only .*jpg or .*png accepted.")
    }
}

function drawResult(response){
    let colorPalette = ["red", "orange","cyan", "sky blue", "blue", "magenta", "pink", "yellow"]
    canvas.width = 256; // img_width form index.js
    canvas.height = 256; // img_height from index.js
    ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height); //x,y,w,h
    ctx.drawImage(image, 0,0); // is it selected image? double check
    for (const [i, v] of response["bbox"].entries()){
        bbox = response["bbox"][i]
        label = response["label"][i]
        score = response["score"][i]
        ctx.beginPath();
        ctx.lineWidth="4";

        ctx.strokeStyle=colorPalette[i];
        ctx.fillStyle=colorPalette[i];
        
        ctx.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]);
        ctx.stroke(); // draw it 
        ctx.font="10px Arial";
        let content = label + " " + parseFloat(score).toFixed(2);
        ctx.fillText(content, bbox[0], bbox[1] < 20 ? bbox[1] + 30 : bbox[1]-5);
    }
}

function communicate(img_base64_url) {
    $.ajax({
      url: "http://localhost:5000/predict/",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify({"image": img_base64_url}),
      dataType: "json"
    }).done(function(response_data) {
        drawResult(response_data.results);
        $("#results").text("Results")
        $("#disease").text("Found " + response_data.results['label']);
    });
  }
  