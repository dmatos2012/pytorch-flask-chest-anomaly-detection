const canvas = document.getElementById('canvas');
const image = document.getElementById('selected-image'); 

let base64Image;
let img_width;
let img_height;

function drawObject(response){
    canvas.width = img_width;
    canvas.height = img_height;
    ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height); //x,y,w,h
    ctx.drawImage(image, 0,0); // is it selected image? double check
    for (const [i, v] of response["bbox"].entries()){
        bbox = response["bbox"][i]
        label = response["label"][i]
        score = response["score"][i]
        ctx.beginPath();
        ctx.lineWidth="4";

        ctx.strokeStyle="red";
        ctx.fillStyle="red";
        
        ctx.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]);
        ctx.stroke(); // draw it 
        ctx.font="30px Arial";
        let content = label + " " + parseFloat(score).toFixed(2);
        ctx.fillText(content, bbox[0], bbox[1] < 20 ? bbox[1] + 30 : bbox[1]-5);
        
    }
    
    // console.log("response " + response['bbox'])
    // for (const bboxInfo of response) {
    //     bbox = bboxInfo['bbox']
    //     console.log(bbox)
    //     label = bboxInfo['label']
    //     console.log(label)
    //     score = bboxInfo['score']
    //     ctx.beginPath();
    //     ctx.lineWidth="4";

    //     ctx.strokeStyle="red";
    //     ctx.fillStyle="red";
        
    //     ctx.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]);
    //     ctx.stroke(); // draw it 
    //     ctx.font="30px Arial";
    //     let content = label + " " + parseFloat(score).toFixed(2);
    //     ctx.fillText(content, bbox[0], bbox[1] < 20 ? bbox[1] + 30 : bbox[1]-5);
       
    // }
    // const object = {'a': [[1,2,3,4],[4,6,7,8]], 'b': [4,4], 'c' : [10,4]};
    // console.log(object.length)
}

// do this when image is uploaded
$("#image").change(function() {
    let reader = new FileReader(); //read data from upload file
    reader.onload = function(e) { // onload assumes successful load.
        let dataURL = reader.result; // data as a base64 encoded string.
        $('#selected-image').attr("src", dataURL); // sets the src attribute(of selected-image) to be the result of upload file
        var img = new Image();
        img.src = dataURL;
        img.onload = function(){
            img_width = img.width;
            img_height = img.height;
        }
        base64Image = dataURL.replace("data:image/png;base64,",""); //replaces "data/...." with "" which is nothing.
    }
    let file = $("#image")[0].files[0];
    reader.readAsDataURL(file); // get underlying input element from jquery object, and then we access the file.
    

    //reset pred text as empty
    $("#prediction").text("");
});
$("#predict-button").click(function(){
    let message = {image: base64Image}
    // you could also use 127.0.0.1 instead of 0.0.0.0 
    $.post("http://localhost:5000/predict/", JSON.stringify(message), function(response){

        $("#prediction").text("results" + response.results);
        drawObject(response.results);
        // console.log(response.bbox);
        
    });
});       