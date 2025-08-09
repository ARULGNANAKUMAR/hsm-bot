import React, { useState, useEffect, useRef } from 'react';

const HospitalChatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userType, setUserType] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const messagesEndRef = useRef(null);

  // Sample commands structure similar to your Python backend
  const commands = {
    common: {
      help: ['help', 'commands', 'what can you do'],
      login: ['login', 'sign in'],
      logout: ['logout', 'sign out'],
      exit: ['exit', 'quit', 'goodbye']
    },
    doctor: {
      search_patient: ['find patient', 'search patient', 'lookup patient'],
      patient_details: ['patient details', 'get patient info'],
      admission_history: ['admission history', 'patient admissions'],
      create_prescription: ['new prescription', 'prescribe medication'],
      view_schedule: ['my schedule', 'today\'s appointments'],
      add_note: ['add note', 'write note']
    },
    nurse: {
      medication_list: ['medication list', 'todays medications'],
      record_administration: ['record medication', 'give medication'],
      patient_vitals: ['record vitals', 'patient vitals'],
      view_applications: ['view tests', 'test applications']
    },
    admin: {
      add_staff: ['add staff', 'new staff'],
      generate_report: ['generate report', 'create report']
    }
  };

  // Responses for common queries
  const responses = {
    greetings: ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
    farewells: ['bye', 'goodbye', 'see you', 'exit', 'quit'],
    thanks: ['thank you', 'thanks', 'appreciate'],
    apologies: ['sorry', 'apologize', 'my bad']
  };

  // Scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Add a message to the chat
  const addMessage = (text, sender) => {
    setMessages(prev => [...prev, { text, sender }]);
  };

  // Check if text matches any predefined responses
  const checkResponseType = (text, responseType) => {
    return responses[responseType].some(word => text.includes(word));
  };

  // Handle login
  const handleLogin = () => {
    const staffId = prompt('Enter your Staff ID (e.g., DOC_001 or NUR_001):').trim().toUpperCase();
    const name = prompt('Enter your full name:').trim();
    
    if (!staffId || !name) {
      addMessage('Both Staff ID and name are required.', 'bot');
      return;
    }

    let userType;
    if (staffId.startsWith('DOC_')) {
      userType = 'doctor';
    } else if (staffId.startsWith('NUR_')) {
      userType = 'nurse';
    } else if (staffId.startsWith('ADM_')) {
      userType = 'admin';
    } else {
      addMessage('Invalid staff ID format. Must start with DOC_, NUR_, or ADM_.', 'bot');
      return;
    }

    // In a real app, you would verify credentials with the backend
    setIsLoggedIn(true);
    setUserType(userType);
    setUserInfo({
      id: staffId,
      name,
      type: userType,
      department: 'Cardiology', // Sample department
      contact: '555-123-4567' // Sample contact
    });

    addMessage(`Welcome, ${name}! You're logged in as ${userType}.`, 'bot');
    showHelp();
  };

  // Handle logout
  const handleLogout = () => {
    if (isLoggedIn) {
      addMessage(`Goodbye, ${userInfo.name}! You've been logged out.`, 'bot');
      setIsLoggedIn(false);
      setUserType(null);
      setUserInfo(null);
    } else {
      addMessage('No user is currently logged in.', 'bot');
    }
  };

  // Show help information
  const showHelp = () => {
    let helpText = 'Available commands:\n\n';
    helpText += 'General commands:\n';
    
    Object.entries(commands.common).forEach(([cmd, phrases]) => {
      helpText += `- ${cmd}: ${phrases.slice(0, 3).join(', ')}...\n`;
    });

    if (isLoggedIn) {
      helpText += `\n${userType.charAt(0).toUpperCase() + userType.slice(1)} commands:\n`;
      Object.entries(commands[userType]).forEach(([cmd, phrases]) => {
        helpText += `- ${cmd}: ${phrases.slice(0, 2).join(', ')}...\n`;
      });
    }

    addMessage(helpText, 'bot');
  };

  // Process user input
  const processInput = () => {
    if (!input.trim()) return;

    const userInput = input.toLowerCase();
    addMessage(input, 'user');
    setInput('');

    // Check for greetings
    if (checkResponseType(userInput, 'greetings')) {
      addMessage('Hello! How can I assist you today?', 'bot');
      return;
    }

    // Check for farewells
    if (checkResponseType(userInput, 'farewells')) {
      addMessage('Thank you for using the Hospital Management System. Goodbye!', 'bot');
      if (isLoggedIn) handleLogout();
      return;
    }

    // Check for thanks
    if (checkResponseType(userInput, 'thanks')) {
      addMessage('You\'re welcome! Is there anything else I can help with?', 'bot');
      return;
    }

    // Check for apologies
    if (checkResponseType(userInput, 'apologies')) {
      addMessage('No problem at all. How can I assist you?', 'bot');
      return;
    }

    // Check for help command
    if (userInput.includes('help')) {
      showHelp();
      return;
    }

    // Check for login command
    if (userInput.includes('login')) {
      handleLogin();
      return;
    }

    // Check for logout command
    if (userInput.includes('logout')) {
      handleLogout();
      return;
    }

    // If not logged in, prompt to login
    if (!isLoggedIn) {
      addMessage('Please login first. Type "login" to begin.', 'bot');
      return;
    }

    // Process role-specific commands
    let commandFound = false;
    
    // Check common commands first
    for (const [cmd, phrases] of Object.entries(commands.common)) {
      if (phrases.some(phrase => userInput.includes(phrase))) {
        commandFound = true;
        if (cmd === 'exit') {
          addMessage('Thank you for using the Hospital Management System. Goodbye!', 'bot');
          handleLogout();
        } else {
          addMessage(`Executing ${cmd} command...`, 'bot');
        }
        break;
      }
    }

    // Check role-specific commands if no common command found
    if (!commandFound) {
      for (const [cmd, phrases] of Object.entries(commands[userType])) {
        if (phrases.some(phrase => userInput.includes(phrase))) {
          commandFound = true;
          addMessage(`Executing ${cmd} command for ${userType}...`, 'bot');
          break;
        }
      }
    }

    // If no command matched
    if (!commandFound) {
      addMessage('I didn\'t understand that. Type "help" for available commands.', 'bot');
    }
  };

  // Handle key press (Enter to send)
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      processInput();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h2>🏥 Hospital Management System Chatbot</h2>
        {isLoggedIn && (
          <div className="user-info">
            Logged in as: {userInfo.name} ({userType})
          </div>
        )}
      </div>
      
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
            {message.text.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message here..."
        />
        <button onClick={processInput}>Send</button>
      </div>
    </div>
  );
};

// Simple CSS for the component
const styles = `
  .chatbot-container {
    max-width: 600px;
    margin: 0 auto;
    border: 1px solid #ccc;
    border-radius: 8px;
    overflow: hidden;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    height: 80vh;
  }
  
  .chatbot-header {
    background-color: #1e88e5;
    color: white;
    padding: 15px;
    text-align: center;
  }
  
  .chatbot-header h2 {
    margin: 0;
    font-size: 1.2rem;
  }
  
  .user-info {
    margin-top: 5px;
    font-size: 0.9rem;
    opacity: 0.9;
  }
  
  .chat-messages {
    flex: 1;
    padding: 15px;
    overflow-y: auto;
    background-color: #f9f9f9;
  }
  
  .message {
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 18px;
    max-width: 80%;
    word-wrap: break-word;
  }
  
  .message.user {
    background-color: #1e88e5;
    color: white;
    margin-left: auto;
    border-bottom-right-radius: 4px;
  }
  
  .message.bot {
    background-color: #e1e1e1;
    margin-right: auto;
    border-bottom-left-radius: 4px;
  }
  
  .chat-input {
    display: flex;
    padding: 10px;
    background-color: #fff;
    border-top: 1px solid #ccc;
  }
  
  .chat-input input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-right: 10px;
  }
  
  .chat-input button {
    padding: 10px 15px;
    background-color: #1e88e5;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  
  .chat-input button:hover {
    background-color: #1565c0;
  }
`;

// Add styles to the document
const styleElement = document.createElement('style');
styleElement.innerHTML = styles;
document.head.appendChild(styleElement);

export default HospitalChatbot;