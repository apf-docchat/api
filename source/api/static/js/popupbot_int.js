// Load CSS and JS dynamically
function loadCssAndScripts(callback) {
  const link1 = document.createElement("link");
  link1.href =
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css";
  link1.rel = "stylesheet";
  document.head.appendChild(link1);

  const link2 = document.createElement("link");
  //link2.href = "https://unpkg.com/antd@4.16.13/dist/antd.min.css";
  link2.href = "https://cdnjs.cloudflare.com/ajax/libs/antd/4.16.13/antd.min.css";
  link2.rel = "stylesheet";
  document.head.appendChild(link2);

  const formData = new FormData();
  formData.append("clientid", clientId);
  fetch(`${apiUrl}/internal/css`, {
    method: 'POST',
    body: formData
  })
  .then(response => response.text())
  .then(cssContent => {
    const style = document.createElement('style');
    style.innerHTML = cssContent;
    document.head.appendChild(style);
  })
  .catch(error => console.error('Error fetching CSS:', error));

  const script1 = document.createElement("script");
  //script1.src = "https://unpkg.com/react@17/umd/react.production.min.js";
  script1.src = "https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js";

  script1.onload = () => {
    const script2 = document.createElement("script");
    //script2.src = "https://unpkg.com/react-dom@17/umd/react-dom.production.min.js";
    script2.src = "https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js";
    script2.onload = () => {
      const script3 = document.createElement("script");
      //script3.src = "https://unpkg.com/antd@4.16.13/dist/antd.min.js";
      script3.src = "https://cdnjs.cloudflare.com/ajax/libs/antd/4.16.13/antd.min.js";
      script3.onload = callback;
      document.body.appendChild(script3);
    };
    document.body.appendChild(script2);
  };
  document.body.appendChild(script1);
}

function initializeChatbot(options) {
  const { useState } = React;
  const { Button, Input, Layout, Modal, Spin } = antd;
  const { Header, Content, Footer } = Layout;

  // Import icons from @ant-design/icons
  const {
    SendOutlined,
    handleDownload,
    AudioOutlined,
    StopOutlined,
    MinusOutlined,
    DownloadOutlined,
    ArrowsAltOutlined,
  } = window.icons;

  let mediaRecorder;
  let audioChunks = [];

  const Chatbot = () => {
    const [visible, setVisible] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const [recording, setRecording] = useState(false);
    const [calloutVisible, setCalloutVisible] = useState(false);
    const [waitingForResponse, setWaitingForResponse] = useState(false);

    const showChatbot = () => setVisible(true);
    const hideChatbot = () => {
      setVisible(false);
      hideCallout();
      // Show the callout after a delay
      setTimeout(() => {
        showCallout();
      }, options.callout_delay || 3000);
    };

    const showCallout = () => {
      setCalloutVisible(true);
      console.log("Callout shown");
    };
    const hideCallout = () => {
      setCalloutVisible(false);
      console.log("Callout hidden");
    };

    // Show the callout after a delay
    setTimeout(() => {
      showCallout();
    }, options.callout_delay || 3000);

    function getWebpageBlob() {
      // Get the outerHTML of the webpage
      const webpageHtml = document.documentElement.outerHTML;
      const htmlBlob = new Blob([webpageHtml], { type: "text/html" });
      return htmlBlob;
    }
    const handleDownload = async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("clientid", clientId);
      if (threadId !== "") {
        formData.append("thread_id", threadId);
      }

      const response = await fetch(`${apiUrl}/download`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error("Failed to download file");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", file);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    const handleSendText = async () => {
      if (inputValue.trim()) {
        const newMessage = {
          type: "user",
          text: inputValue,
          handouts: [],
          media: [],
        };
        setMessages([...messages, newMessage]);
        setInputValue("");
        // Create FormData to handle multipart data
        let formData = new FormData();
        formData.append("user_query", inputValue);
    
        const htmlBlob = getWebpageBlob();
        formData.append("webpage", htmlBlob);
        formData.append("clientid", clientId);
        if (threadId !== "") {
          formData.append("thread_id", threadId);
        }
        if (localStorage.getItem('collectionId')) {
          formData.append("collection_id", localStorage.getItem('collectionId'));
        }
    
        // Send message to backend
        setWaitingForResponse(true);
        const response = await fetch(`${apiUrl}/internal/text`, {
          method: "POST",
          body: formData,
        });
    
        const data = await response.json();
        setWaitingForResponse(false);
        threadId = data.thread_id;
        if (data.function == 'chat') {
          setMessages([
            ...messages,
            newMessage,
            {
              type: "bot",
              text: data.ai_message,
              handouts: data.handouts,
              media: data.media,
            },
          ]);
        } else if (data.function == 'choose_collection') {
          // Convert each item in data.collections to a button HTML string
          const collectionButtonsHtml = data.collections.map((collection) => {
            return `<button onclick="handleCollectionClick(${collection.collection_id}, '${collection.collection_name}')">${collection.collection_name}</button>`;
          }).join(" ");
    
          // Add the collection buttons to the messages as HTML
          setMessages([
            ...messages,
            newMessage,
            {
              type: "bot",
              text: `${data.ai_message}<br>${collectionButtonsHtml}`,
              handouts: data.handouts,
              media: data.media,
            },
          ]);
        }
      }
    };
    
    // Define the handleCollectionClick function globally
    window.handleCollectionClick = async (collectionId, collectionName) => {
      //store collectionId for later retrieval and use
      localStorage.setItem('collectionId', collectionId);

      setMessages([
        ...messages,
        {
          type: "bot",
          text: `Collection named <b>${collectionName}</b> selected, your questions will be responded based on the data in this collection.`,
          handouts: [],
          media: [],
        },
      ]);
    };

    const handleVoiceStart = () => {
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        setRecording(true);
        mediaRecorder.ondataavailable = (event) => {
          audioChunks.push(event.data);
        };
        mediaRecorder.onstop = async () => {
          // Stop all tracks in the stream
          stream.getTracks().forEach((track) => track.stop());

          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
          const formData = new FormData();
          formData.append("file", audioBlob, "audio.webm");

          formData.append("clientid", clientId);

          if (threadId !== "") {
            formData.append("thread_id", threadId);
          }

          // Send audio to backend
          setWaitingForResponse(true);
          const response = await fetch(`${apiUrl}/voice`, {
            method: "POST",
            body: formData,
          });
          const data = await response.json();
          console.log(data);
          setWaitingForResponse(false);
          audioChunks = [];

          /* threadId = data.thread_id;
                    setMessages([...messages, { type: 'user', text: data.user_message }, { type: 'bot', text: data.ai_message }]);

                    // Update the innerHTML of the div with id 'html-placeholder'
                    //console.log('Webpage content:', data.webpage_content);
                    if (data.webpage_content) {
                        const htmlPlaceholderDiv = document.getElementById('html-placeholder');
                        if (htmlPlaceholderDiv) {
                            htmlPlaceholderDiv.innerHTML = data.webpage_content;
                            console.log('Webpage content updated');
                        }
                    } */
          /* const newMessage = {
            type: "user",
            text: data.user_message,
            handouts: [],
            media: [],
          };
          setMessages([...messages, newMessage]);

          // Create FormData to handle multipart data
          let formData2 = new FormData();
          formData2.append("user_query", data.user_message);

          const htmlBlob = getWebpageBlob();
          formData2.append("webpage", htmlBlob);
          formData2.append("clientid", clientId);
          if (threadId !== "") {
            formData2.append("thread_id", threadId);
          }

          // Send message to backend
          setWaitingForResponse(true);
          const response2 = await fetch(`${apiUrl}/internal/text`, {
            method: "POST",
            body: formData2,
          });

          const data2 = await response2.json();
          setWaitingForResponse(false);
          threadId = data2.thread_id;
          setMessages([
            ...messages,
            newMessage,
            { type: "bot", text: data2.ai_message, handouts: [], media: [] },
          ]);

          // Update the innerHTML of the div with id 'html-placeholder'
          //console.log('Webpage content:', data.webpage_content);
          if (data2.webpage_content) {
            const htmlPlaceholderDiv =
              document.getElementById("html-placeholder");
            if (htmlPlaceholderDiv) {
              htmlPlaceholderDiv.innerHTML = data2.webpage_content;
              console.log("Webpage content updated");
            }
          } */
          setInputValue(data.user_message);
          //handleSendText();
        };
      });
    };

    const handleVoiceStop = async () => {
      if (mediaRecorder) {
        mediaRecorder.stop();
      }
      setRecording(false);
    };

    function computePosition(value, offset, dimension) {
      if (typeof value === "string" && value.includes("calc")) {
        // Handle calc expressions
        return `calc(${value.match(/calc\((.*)\)/)[1]} + ${offset}px)`;
      } else if (typeof value === "string" && value.includes("px")) {
        // Handle pixel values
        const numericValue = parseFloat(value);
        return `${numericValue + offset}px`;
      } else if (typeof value === "string" && value.includes("%")) {
        // Handle percentage values
        const numericValue = parseFloat(value);
        const dimensionValue =
          dimension === "height" ? window.innerHeight : window.innerWidth;
        return `calc(${numericValue}% + ${offset}px)`;
      } else {
        // Default case
        return `${offset}px`;
      }
    }

    return React.createElement(
      React.Fragment,
      null,
      !visible &&
        React.createElement(Button, {
          id: "chat_icon",
          // style: {
          //   position: "fixed",
          //   bottom: options.icon_position.bottom || "20px",
          //   right: options.icon_position.right || "calc(50%)",
          //   zIndex: 9999,
          //   width: "50px",
          //   height: "50px",
          //   cursor: "pointer",
          //   padding: 0,
          //   backgroundColor: "transparent",
          // },
          onClick: showChatbot,
          icon: React.createElement("img", {
            src:
              options.icon_url || `${baseUrl}/static/images/ai-chat.png`,
            // style: { width: "50px", height: "50px" },
            alt: "Chatbot",
          }),
        }),

      // !visible &&
      //   calloutVisible &&
      //   React.createElement(
      //     "div",
      //     {
      //       style: {
      //         position: "fixed",
      //         bottom:
      //           computePosition(options.icon_position.bottom, 50, "height") ||
      //           "70px",
      //         right:
      //           computePosition(options.icon_position.right, -110, "width") ||
      //           "calc(50% - 110px)",
      //         zIndex: 10000,
      //         backgroundColor: "white",
      //         border: "1px solid #ccc",
      //         borderRadius: "5px",
      //         padding: "10px",
      //         paddingRight: "30px",
      //         boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
      //         display: "flex",
      //         alignItems: "center",
      //         opacity: calloutVisible ? 1 : 0,
      //         transform: calloutVisible ? "translateY(0)" : "translateY(20px)",
      //         transition: "opacity 0.3s ease, transform 0.3s ease",
      //       },
      //       onClick: showChatbot,
      //     },
      //     React.createElement(
      //       "span",
      //       null,
      //       options.callout_text || "Click to speak!   "
      //     )
      //   ),
      // !visible &&
      //   calloutVisible &&
      //   React.createElement(
      //     "button",
      //     {
      //       onClick: hideCallout,
      //       style: {
      //         position: "fixed",
      //         bottom:
      //           computePosition(options.icon_position.bottom, 75, "height") ||
      //           "95px",
      //         right:
      //           computePosition(options.icon_position.right, -115, "width") ||
      //           "calc(50% - 115px)",
      //         zIndex: 10001,
      //         marginLeft: "10px",
      //         background: "none",
      //         border: "none",
      //         cursor: "pointer",
      //         fontSize: "13px",
      //         lineHeight: "16px",
      //       },
      //     },
      //     "✖"
      //   ),

      React.createElement(
        Modal,
        {
          visible: visible,
          onCancel: hideChatbot,
          footer: null,
          // bodyStyle: {
          //   padding: 0,
          // },
          // id: "chat_model",
          style: {
            // position: "fixed",
            // bottom: "20px",
            // right: "20px",
            // width: "350px",
            // height: "500px",
            // padding: 0,
            // overflow: "hidden",
            // top: "auto",
          },
        },
        React.createElement(
          Layout,
          {
            id: "chatbot",
            // style: {
            //   position: "fixed",
            //   bottom: options.chatwindow_position.bottom || "20px",
            //   right: options.chatwindow_position.right || "20px",
            //   width: options.chatwindow_size.width || "350px",
            //   height: options.chatwindow_size.height || "500px",
            //   padding: 0,
            //   overflow: "hidden",
            //   zIndex: 99999,
            //   borderRadius: "15px",
            //   display: "flex",
            //   flexDirection: "column",
            //   backgroundColor: "#FFFFFF",
            // },
          },
          React.createElement(
            Header,
            {
              id: "chatbotTitleBar",
              // style: {
              //   display: "flex",
              //   alignItems: "center",
              //   gap: "15px",
              //   justifyContent: "flex-start",
              //   backgroundColor: "#FFFFFF",
              //   color: "white",
              //   textAlign: "center",
              //   borderTopLeftRadius: "15px",
              //   borderTopRightRadius: "15px",
              //   lineHeight: "30px",
              //   padding: "10px 16px",
              //   fontSize: "16px",
              //   borderBottom: "1px solid #e8e8e8",
              // },
              // className: "chat_header",
            },
            React.createElement("img", {
              src: `${baseUrl}/static/images/ai-chat-header.png`,
              alt: "Logo",
              // style: {
              //   width: "40px",
              //   height: "40px",
              // },
            }),
            React.createElement(
              "div",
              {
                id: "chatbotTitleWrapper",
                // style: {
                //   display: "flex",
                //   flexDirection: "column",
                //   alignItems: "flex-start",
                // },
              },
              React.createElement(
                "p",
                {
                  id: "chatbotTitleText",
                  // style: {
                  //   margin: "0px",
                  //   fontSize: "16px",
                  //   fontWeight: "700",
                  //   lineHeight: "19.36px",
                  //   textAlign: "left",
                  //   color: "#000000",
                  // },
                },
                "Document Chatbot"
              ),
              React.createElement(
                "p",
                {
                  // style: {
                  //   margin: "0px",
                  //   fontSize: "12px",
                  //   fontWeight: "400",
                  //   lineHeight: "14.52px",
                  //   textAlign: "left",
                  //   color: "#7F7F7F",
                  // },
                },
                /* "Powered by ..." */
              )
            ),
            // React.createElement("p", null, options.title || "Document Bot"),
            React.createElement(Button, {
              icon: React.createElement(MinusOutlined, null),
              id: "closeButton",
              // style: {
              //   marginLeft: "auto",
              //   borderRadius: "25px",
              //   backgroundColor: "#F5F5F5",
              //   border: "none",
              //   color: "black",
              //   fontWeight: "700",
              // },
              onClick: hideChatbot,
            })
          ),
          React.createElement(
            Content,
            {
              id: "chatLog",
              // style: {
              //   flexGrow: 1,
              //   overflowY: "auto",
              //   padding: "15px",
              //   scrollbarWidth: "thin", // For Firefox
              //   scrollbarColor: "#888 #f1f1f1",
              // },
            },
            messages.map((msg, index) =>
              React.createElement(
                "div",
                {
                  id: `message_wrapper`,
                  key: index,
                  style: {
                    display: "flex",
                    flexDirection: msg.type === "user" ? "row-reverse" : "row",
                    gap: "10px",
                  },
                },
                msg.type !== "user" &&
                  React.createElement("img", {
                    src: `${baseUrl}/static/images/ai-chat-header.png`,
                    alt: "Logo",
                    id: "chatbotAvatar",
                    // style: {
                    //   width: "30px",
                    //   height: "30px",
                    //   alignSelf: "flex-end",
                    //   marginBottom: "10px",
                    // },
                  }),
                React.createElement(
                  "div",
                  {
                    id: "message",
                    // style: {
                    //   backgroundColor:
                    //     msg.type === "user" ? "#FFFFFF" : "#F5F5F5",
                    //   padding: "10px",
                    //   borderRadius: msg.type === "user" ? "30px" : "10px",
                    //   alignSelf:
                    //     msg.type === "user" ? "flex-end" : "flex-start",
                    //   boxShadow:
                    //     msg.type === "user" ? "#d7d7d7 2px 4px 10px" : null,
                    //   marginBottom: "10px",
                    // },
                    className:
                      msg.type === "user" ? "user_message" : "bot_message",
                  },
                  React.createElement("p", {
                    // style: {
                    //   margin: "0px",
                    // },
                    dangerouslySetInnerHTML: { __html: msg.text },
                  }),
                  msg.media.map((m, index) =>
                    // React.createElement("iframe", {
                    //   style: {
                    //     width: "100%",
                    //   },
                    //   src: `${m}?autoplay=1`,
                    //   frameBorder: "0",
                    // })
                    React.createElement(
                      "div",
                      {},
                      React.createElement("iframe", {
                        // style: {
                        //   width: "100%",
                        // },
                        src: `${m}?autoplay=1`,
                        frameBorder: "0",
                      })
                      // React.createElement(
                      //   "div",
                      //   {
                      //     id: "videoControls",
                      //   },
                      //   React.createElement("a", {}, "Watch on Youtube"),
                      //   React.createElement(Button, {
                      //     icon: React.createElement(ArrowsAltOutlined, null),
                      //   })
                      // )
                    )
                  ),
                  //   msg.handouts.map((file, index) =>
                  //     React.createElement(
                  //       "button",
                  //       {
                  //         style: {
                  //           float: "right",
                  //           color: "white",
                  //           backgroundColor: "blue",
                  //         },
                  //         onClick: () => handleDownload(file),
                  //       },
                  //       `Download ${file}`
                  //     )
                  //   )
                  msg.handouts.map((file, index) =>
                    React.createElement(
                      "div",
                      {
                        id: "videoControls",
                        // style: {
                        //   display: "flex",
                        //   justifyContent: "space-between",
                        //   alignItems: "flex-end",
                        //   marginTop: "10px",
                        // },
                        onClick: () => handleDownload(file),
                      },
                      React.createElement(
                        "a",
                        {
                          // style: {
                          //   textDecoration: "underline",
                          // },
                        },
                        //"Download Report"
                        `Download ${file}`
                      ),
                      React.createElement(Button, {
                        // style: {
                        //   border: "none",
                        //   backgroundColor: "#f5f5f5",
                        // },
                        icon: React.createElement(DownloadOutlined, null),
                      })
                    )
                  )
                )
              )
            ),
            waitingForResponse &&
              React.createElement(
                "div",
                { className: "waiting-icon" },
                React.createElement(Spin)
              )
          ),
          React.createElement(
            Footer,
            {
              id: "inputGroupWrapper",
              // style: {
              //   padding: "0px",
              //   backgroundColor: "#ffffff",
              //   boxSizing: "border-box",
              //   borderTop: "1px solid #e8e8e8",
              // },
            },
            React.createElement(
              Input.Group,
              {
                compact: true,
                id: "inputGroup",
                // style: {
                //   position: "relative",
                // },
              },
              React.createElement(Input, {
                // style: { width: "calc(100% - 70px)" },
                // style: {
                //   position: "relative",
                //   border: "none",
                //   width: "calc(100% - 40px)",
                //   lineHeight: "35px",
                // },
                placeholder: "Ask a question...",
                value: inputValue,
                onChange: (e) => setInputValue(e.target.value),
                onPressEnter: handleSendText,
              }),
              inputValue &&
                inputValue.trim() !== "" &&
                React.createElement(Button, {
                  // style: {
                  //   position: "absolute",
                  //   right: "0px",
                  //   top: "50%",
                  //   transform: "translateY(-50%)",
                  //   border: "none",
                  // },
                  icon: React.createElement(SendOutlined, null),
                  onClick: handleSendText,
                }),
              //   recording
              //     ? React.createElement(Button, {
              //         style: { position: "absolute", right: "0" },
              //         icon: React.createElement(SendOutlined, null),
              //         onClick: handleVoiceStop,
              //       })
              //     : React.createElement(Button, {
              //         style: { position: "absolute", right: "0" },
              //         icon: React.createElement(AudioOutlined, null),
              //         onClick: handleVoiceStart,
              //       })
              inputValue.trim() === "" && recording
                ? React.createElement(Button, {
                    // style: {
                    //   position: "absolute",
                    //   right: "0px",
                    //   top: "50%",
                    //   transform: "translateY(-50%)",
                    //   border: "none",
                    // },
                    icon: React.createElement(SendOutlined, null),
                    onClick: handleVoiceStop,
                  })
                : null,
              inputValue.trim() === "" && !recording
                ? React.createElement(Button, {
                    // style: {
                    //   position: "absolute",
                    //   right: "0px",
                    //   top: "50%",
                    //   transform: "translateY(-50%)",
                    //   border: "none",
                    // },
                    icon: React.createElement(AudioOutlined, null),
                    onClick: handleVoiceStart,
                  })
                : null
            )
          )
        )
      )
    );
  };

  // Add custom scrollbar styles for WebKit browsers (Chrome, Safari)
  const customScrollbarCSS = `
    #chatLog::-webkit-scrollbar {
        width: 8px;
    }
    #chatLog::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    #chatLog::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    #chatLog::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    `;

  const rootElement = document.createElement("div");
  rootElement.id = "root";
  document.body.appendChild(rootElement);
  ReactDOM.render(React.createElement(Chatbot), rootElement);
}

function loadIcons(chatbotSettings) {
  // Load @ant-design/icons dynamically
  const scriptIcons = document.createElement("script");
  //scriptIcons.src = "https://unpkg.com/@ant-design/icons@4.7.0/dist/index.umd.min.js";
  scriptIcons.src = "https://cdnjs.cloudflare.com/ajax/libs/ant-design-icons/4.7.0/index.umd.min.js";
  scriptIcons.onload = () => {
    window.antdIcons = window.icons;
    initializeChatbot(chatbotSettings);
  };
  document.body.appendChild(scriptIcons);
}

console.log("commencing document chatbot...");
var clientId = myScriptData.clientId;

const baseUrl = myScriptData.API_BASE_URL || "https://api.pwdev.internal.nlightnconsulting.com";
const apiUrl = `${baseUrl}/api/v2/popupbot`;
let threadId = "";

// log the visit & fetch chatbot settings
async function fetchChatbotSettings() {
  const formData = new FormData();
  formData.append("clientid", clientId);

  console.log("Fetching chatbot settings...");
  const response = await fetch(`${apiUrl}/visit`, {
    method: "POST",
    body: formData,
  });

  const settings = await response.json();
  return {
    title: settings.title,
    icon_url: settings.icon_url,
    callout_text: settings.callout_text,
    callout_delay: settings.callout_delay,
    mode: settings.mode,
  };
}

const style = `
  .login_wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background-color: #f5f5f5;
  }
  
  .login_card {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    width: 300px;
  }
  
  .login-form {
    display: flex;
    flex-direction: column;
  }
  
  .form-item {
    margin-bottom: 15px;
  }
  
  .input-group input {
    width: 100%;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
  }
  
  .primary-button {
    width: 100%;
    padding: 10px;
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  
  .primary-button:hover {
    background-color: #40a9ff;
  }
  
  .divider {
    text-align: center;
    margin: 15px 0;
    color: #888;
  }
  `;
  
  // Create a style element and append it to the document head
  const styleTag = document.createElement('style');
  styleTag.innerHTML = style;
  document.head.appendChild(styleTag);


/* document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login_form");
  const msLoginButton = document.getElementById("ms_login_button");

  // Handle username/password login
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch(`${apiUrl}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem("token", data.data.token);
        localStorage.setItem("username", username);
        localStorage.setItem("isAdmin", data.data.sysadmin);
        alert("Login successful!");
        initializeChatbot(); // Initialize chatbot after login
      } else {
        const errorData = await response.json();
        alert(`Login failed: ${errorData.message}`);
      }
    } catch (error) {
      console.error("Error during login:", error);
      alert("An error occurred during login.");
    }
  });

  // Handle MS 365 login
  msLoginButton.addEventListener("click", () => {
    window.open(`${apiUrl}/loginms365`, "_self");
  });
}); */

// Ensure chatbot doesn't initialize without login
/* function initializeChatbot() {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in to use the chatbot.");
    return;
  }
// log the visit and fetch chatbot settings
fetchChatbotSettings().then((chatbotSettings) => {
  loadCssAndScripts(() => loadIcons(chatbotSettings));
});
} */

// log the visit and fetch chatbot settings
fetchChatbotSettings().then((chatbotSettings) => {
  loadCssAndScripts(() => loadIcons(chatbotSettings));
});