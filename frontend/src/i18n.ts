export type Language = 'ta' | 'en';

export const translations = {
  ta: {
    appTitle: "பார்ம் சாத்தி",
    tagline: "விவசாயிகளுக்கான நவீன பாசன ஆட்டோமேஷன்",
    easyMode: "எளிய முறை",
    advMode: "முழு முறை",
    greetingMorning: "வணக்கம்! காலை வணக்கம்",
    greetingAfternoon: "வணக்கம்! மதிய வணக்கம்",
    greetingEvening: "வணக்கம்! மாலை வணக்கம்",
    
    // Nav
    navHome: "முகப்பு",
    navPipelines: "7-பைப்லைன்",
    navSchedules: "பாசன திட்டம்",
    navAlerts: "அறிவிப்புகள்",
    navSettings: "அமைப்புகள்",
    
    // Motor control
    registeredMotors: "பதிவுசெய்த மோட்டார்கள்",
    statusRunning: "இயங்குகிறது",
    statusStopped: "நிறுத்தப்பட்டுள்ளது",
    statusFault: "பாதுகாப்பு நிறுத்தம் (பிழை)",
    statusOffline: "இணைப்பில்லை (ஆஃப்லைன்)",
    startMotor: "மோட்டாரை இயக்கு (START)",
    stopMotor: "மோட்டாரை நிறுத்து (STOP)",
    emergencyStop: "அவசர நிறுத்தம் (EMERGENCY)",
    contactorClosed: "கான்டாக்டர் இணைக்கப்பட்டது",
    confirmStart: "மோட்டாரை இயக்க உறுதியாக விரும்புகிறீர்களா?",
    confirmStop: "மோட்டாரை உடனடியாக நிறுத்த விரும்புகிறீர்களா?",
    confirmYes: "ஆம், இயக்கு",
    confirmStopYes: "ஆம், நிறுத்து",
    cancel: "ரத்து செய்",
    
    // Live Telemetry
    electricalHealth: "மின்சார நிலை & சென்சார்கள்",
    voltage: "மின்னழுத்தம் (Voltage)",
    current: "மின்சாரம் (Current)",
    frequency: "அதிர்வெண்",
    flowRate: "நீர் வரத்து (Flow Rate)",
    litresPerMin: "லிட்டர்/நிமிடம்",
    controllerTemp: "கன்ட்ரோலர் வெப்பம்",
    signalStrength: "சிக்னல் வலிமை",
    runtimeHours: "மொத்த ஓட்டம்",
    hours: "மணிநேரம்",
    
    // 7-Pipeline
    pipelineTitle: "7-பைப்லைன் சுழல் பாசன அமைப்பு",
    pipelineSub: "ஒவ்வொரு பைப்லைனிலும் 5 சுழற்சிகள் முடித்து அடுத்ததற்கு மாறும்",
    activePipeline: "தற்போதைய பாசன பைப்லைன்",
    rotationsCompleted: "முடிந்த சுழற்சிகள்",
    targetRotations: "தேவையான சுழற்சிகள்",
    nextPipeline: "அடுத்த பைப்லைன்",
    resetSequence: "வரிசையை மீட்டமை (Line 1)",
    rotaryObstructed: "சுழல் வால்வு அடைப்பு ஏற்பட்டுள்ளது!",
    
    // Schedules
    scheduleTitle: "திட்டமிடப்பட்ட பாசனம்",
    addSchedule: "புதிய பாசன நேரம் சேர்",
    scheduleName: "திட்டத்தின் பெயர்",
    startTime: "தொடக்க நேரம்",
    stopTime: "நிறுத்தும் நேரம்",
    duration: "பாசன காலம் (நிமிடங்கள்)",
    activeDays: "இயங்கும் நாட்கள்",
    all7PipelineMode: "7 பைப்லைன்களும் வரிசையாக (5 சுழற்சி/வரிசை)",
    saveSchedule: "திட்டத்தை சேமி",
    noSchedules: "திட்டங்கள் எதுவும் இல்லை",
    
    // Faults & Alerts
    alertsTitle: "பாதுகாப்பு எச்சரிக்கைகள் & அறிவிப்புகள்",
    noAlerts: "தற்போது எந்த எச்சரிக்கைகளும் இல்லை. மோட்டார் பாதுகாப்பாக உள்ளது.",
    cause: "காரணம்:",
    safeAction: "பாதுகாப்பான தீர்வு:",
    markResolved: "பிழையை சரிசெய்து மீட்டமை",
    
    // Voice Assistant
    voiceTitle: "பார்ம் சாத்தி குரல் உதவியாளர்",
    voiceListening: "கேட்கிறது... பேசுங்கள்...",
    voiceSpeakPrompt: "'மோட்டார் ஓடுகிறதா?' அல்லது 'மோட்டார் போடு' என்று கேட்கவும்",
    voiceSend: "அனுப்பு",
    voicePlaceholder: "குரல் அல்லது தட்டச்சு வழியாக கேளுங்கள்...",
    voiceConfirmAction: "குரல் கட்டளை உறுதிப்படுத்தல்",

    // Technician / Simulator
    techPanel: "தொழில்நுட்ப & சோதனைக் குழு",
    hardwareStatus: "FS-CTRL-88219 ஹார்டுவேர் கன்ட்ரோலர்",
    normalState: "இயல்பு நிலை",
    injectFault: "செயற்கை பிழை தூண்டுதல் (சோதனைக்கு):",
    injectUnderVolt: "குறைந்த மின்னழுத்தம் (165V)",
    injectOverload: "கூடுதல் சுமை (28.5A)",
    injectDryRun: "தண்ணீரின்றி ஓடுதல் (Dry-Run 4.2A)",
    injectObstruction: "சுழல் வால்வு அடைப்பு (Obstruction)",
    clearFaults: "அனைத்து பிழைகளையும் நீக்கு",

    // Auth
    loginTitle: "பார்ம் சாத்தி லாகின்",
    phoneNumber: "கைபேசி எண் (10 இலக்கம்)",
    password: "ரகசியக் குறியீடு (Password)",
    loginBtn: "உள்நுழை (Login)",
    registerBtn: "புதிய கணக்கு உருவாக்கு",
    testCredentials: "டெமோ கணக்கு: 9876543210 / FarmerPass123!"
  },
  en: {
    appTitle: "Farm Saathi",
    tagline: "Smart Farmer Irrigation & Motor Automation",
    easyMode: "Easy Mode",
    advMode: "Advanced Mode",
    greetingMorning: "Good Morning, Farmer",
    greetingAfternoon: "Good Afternoon, Farmer",
    greetingEvening: "Good Evening, Farmer",

    // Nav
    navHome: "Home",
    navPipelines: "7-Pipelines",
    navSchedules: "Schedules",
    navAlerts: "Alerts",
    navSettings: "Settings",

    // Motor control
    registeredMotors: "Registered Motors",
    statusRunning: "RUNNING",
    statusStopped: "STOPPED",
    statusFault: "SAFETY FAULT",
    statusOffline: "OFFLINE",
    startMotor: "START MOTOR",
    stopMotor: "STOP MOTOR",
    emergencyStop: "EMERGENCY STOP",
    contactorClosed: "Contactor Latched & Flowing",
    confirmStart: "Are you sure you want to start the motor?",
    confirmStop: "Are you sure you want to stop the motor now?",
    confirmYes: "Yes, Start Motor",
    confirmStopYes: "Yes, Stop Motor",
    cancel: "Cancel",

    // Live Telemetry
    electricalHealth: "Live Sensors & Electrical Health",
    voltage: "Voltage (V)",
    current: "Current (A)",
    frequency: "Frequency",
    flowRate: "Water Flow Rate",
    litresPerMin: "LPM",
    controllerTemp: "Controller Temp",
    signalStrength: "Signal RSSI",
    runtimeHours: "Total Runtime",
    hours: "hrs",

    // 7-Pipeline
    pipelineTitle: "7-Pipeline Rotary Distributor System",
    pipelineSub: "Completes 5 rotations on each line before stepping to next pipeline",
    activePipeline: "Active Irrigation Pipeline",
    rotationsCompleted: "Completed Rotations",
    targetRotations: "Target Rotations",
    nextPipeline: "Next Pipeline",
    resetSequence: "Reset Sequence to Line 1",
    rotaryObstructed: "Rotary valve obstructed / jammed!",

    // Schedules
    scheduleTitle: "Automated Irrigation Schedules",
    addSchedule: "Add New Schedule",
    scheduleName: "Schedule Name",
    startTime: "Start Time",
    stopTime: "Stop Time",
    duration: "Duration (Minutes)",
    activeDays: "Active Days",
    all7PipelineMode: "Sequential 7 Pipelines (5 rot/line)",
    saveSchedule: "Save Schedule",
    noSchedules: "No schedules configured yet",

    // Faults & Alerts
    alertsTitle: "Safety Faults & Event Notifications",
    noAlerts: "No active faults. All motors and sensors operating normally.",
    cause: "Explanation:",
    safeAction: "Safe Farmer Action:",
    markResolved: "Verify and Reset Fault",

    // Voice Assistant
    voiceTitle: "Farm Saathi Voice Assistant",
    voiceListening: "Listening... Please speak...",
    voiceSpeakPrompt: "Ask 'Is my motor running?' or 'Start borewell motor'",
    voiceSend: "Ask",
    voicePlaceholder: "Speak or type your question...",
    voiceConfirmAction: "Confirm Voice Command",

    // Technician / Simulator
    techPanel: "Technician & Hardware Diagnostics",
    hardwareStatus: "FS-CTRL-88219 Hardware Controller",
    normalState: "Normal Running",
    injectFault: "Inject Fault Simulation (Safety Test):",
    injectUnderVolt: "Low Voltage Sag (165V)",
    injectOverload: "Motor Overload (28.5A)",
    injectDryRun: "Dry-Run No Water (4.2A)",
    injectObstruction: "Rotary Obstruction / Jam",
    clearFaults: "Clear Injected Faults",

    // Auth
    loginTitle: "Farm Saathi Login",
    phoneNumber: "Phone Number (10 digits)",
    password: "Password",
    loginBtn: "Sign In",
    registerBtn: "Register New Farmer Account",
    testCredentials: "Demo Login: 9876543210 / FarmerPass123!"
  }
};
