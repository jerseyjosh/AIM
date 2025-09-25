// BE Email Generator JavaScript

// Global variables
let credentials = null;
let currentEmailType = 'be';
let emailConfigs = {}; // Will hold email type configurations
let emailData = {
    news_stories: [],
    business_stories: [],
    sports_stories: [],
    community_stories: [],
    podcast_stories: [],
    family_notices: [],
    weather: {
        todays_weather: '',
        tides: '',
        date: ''
    },
    connect_cover_image: '',
    // Adverts
    vertical_adverts: [],
    horizontal_adverts: []
};

// Backend URL - change this if running backend on different port
const BACKEND_URL = 'http://localhost:8000';

// Add global error handling
window.addEventListener('error', function(e) {
    console.error('=== GLOBAL ERROR ===', e);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('=== UNHANDLED PROMISE REJECTION ===', e);
});

window.addEventListener('beforeunload', function(e) {
    console.error('=== PAGE IS ABOUT TO UNLOAD ===');
});

// Load email configurations from backend
async function loadEmailConfigs() {
    try {
        const response = await fetch('/api/email-configs');
        if (!response.ok) {
            throw new Error(`Failed to load email configs: ${response.status}`);
        }
        const data = await response.json();
        
        // Convert array to object for easier lookup
        emailConfigs = {};
        data.email_types.forEach(config => {
            emailConfigs[config.id] = config;
        });
        
        console.log('Loaded email configurations:', emailConfigs);
        return emailConfigs;
    } catch (error) {
        console.error('Error loading email configurations:', error);
        // Fallback to default config
        emailConfigs = {
            'be': { id: 'be', name: 'Bailiwick Express (Jersey)', advert_type: 'vertical_horizontal', ui_features: {} },
            'ge': { id: 'ge', name: 'Bailiwick Express (Guernsey)', advert_type: 'vertical_horizontal', ui_features: {} },
            'jep': { id: 'jep', name: 'Jersey Evening Post', advert_type: 'single', ui_features: {} }
        };
        return emailConfigs;
    }
}

// Get configuration for current email type
function getCurrentConfig() {
    return emailConfigs[currentEmailType] || emailConfigs['be'] || {};
}

// Check if current email type supports a feature
function supportsFeature(feature) {
    const config = getCurrentConfig();
    return config.ui_features && config.ui_features[feature] === true;
}

// Initialize the app
document.addEventListener('DOMContentLoaded', async function() {
    // Load email configurations first
    await loadEmailConfigs();
    
    // Set default dates
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    document.getElementById('deathsStart').value = yesterday.toISOString().split('T')[0];
    document.getElementById('deathsEnd').value = today.toISOString().split('T')[0];
    
    // Initialize email type
    switchEmailType();
    
    // Initialize preview area with a welcome message
    const preview = document.getElementById('livePreview');
    if (preview) {
        preview.srcdoc = '<div style="padding: 40px; text-align: center; font-family: Arial, sans-serif;"><h3>Email Generator</h3><p>Select an email type and fetch data to get started.</p></div>';
    }
    
    // Show login modal
    const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
    loginModal.show();
});

// Auto-update for live preview
function attachPreviewUpdateListeners() {
    // Top image form
    document.getElementById('topImageTitle').addEventListener('input', debounce(updatePreview, 1000));
    document.getElementById('topImageUrl').addEventListener('input', debounce(updatePreview, 1000));
    document.getElementById('topImageAuthor').addEventListener('input', debounce(updatePreview, 1000));
    document.getElementById('topImageLink').addEventListener('input', debounce(updatePreview, 1000));
    
    // JEP-specific fields
    const jepCover = document.getElementById('jepCover');
    const jepPublication = document.getElementById('jepPublication');
    if (jepCover) jepCover.addEventListener('input', debounce(updatePreview, 1000));
    if (jepPublication) jepPublication.addEventListener('input', debounce(updatePreview, 1000));
}


// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Email type management
function switchEmailType() {
    // Use correct select ID from index.html; fallback for backward compatibility
    const selectEl = document.getElementById('emailTypeSelect') || document.getElementById('emailType');
    if (selectEl) currentEmailType = selectEl.value;
    
    // Update body class to control visibility
    document.body.className = document.body.className.replace(/email-type-\w+/g, '');
    document.body.classList.add(`email-type-${currentEmailType}`);
    
    // Show/hide sections based on email type
    updateVisibilityForEmailType();
    
    // Clear current data when switching types
    emailData = {
        email_type: currentEmailType,
        news_stories: [],
        business_stories: [],
        sports_stories: [],
        community_stories: [],
        podcast_stories: [],
        family_notices: [],
        weather: {
            todays_weather: '',
            tides: '',
            date: ''
        },
        connect_cover_image: '',
        // JEP-specific fields
        jep_cover: '',
        publication: '',
        date: '',
        adverts: [],
        // Adverts for BE/GE
        vertical_adverts: [],
        horizontal_adverts: []
    };
    updateTables();
    updateFamilyNotices();
    updateWeather();
    updateJEPAdverts();
    updateAdvertTables();
    // Don't call updatePreview() here - wait until data is fetched
}

function updateVisibilityForEmailType() {
    const config = getCurrentConfig();
    
    const deathsSection = document.getElementById('deathsSection');
    const jepSection = document.getElementById('jepSection');
    const familyNoticesCard = document.getElementById('familyNoticesCard');
    const weatherCard = document.getElementById('weatherCard');
    const topImageCard = document.getElementById('topImageCard');
    
    // Show/hide sections based on configuration
    if (deathsSection) {
        deathsSection.style.display = supportsFeature('show_family_notices') ? 'block' : 'none';
    }
    
    if (jepSection) {
        jepSection.style.display = supportsFeature('show_publication_cover') ? 'block' : 'none';
    }
    
    if (familyNoticesCard) {
        familyNoticesCard.style.display = supportsFeature('show_family_notices') ? 'block' : 'none';
    }
    
    if (weatherCard) {
        weatherCard.style.display = supportsFeature('show_weather_edit') ? 'block' : 'none';
    }
    
    if (topImageCard) {
        // Show top image for all except JEP (which has publication cover instead)
        topImageCard.style.display = supportsFeature('show_publication_cover') ? 'none' : 'block';
    }
    
    // Show/hide adverts sections based on advert type
    const verticalAdvertsCard = document.getElementById('verticalAdvertsCard');
    const horizontalAdvertsCard = document.getElementById('horizontalAdvertsCard');
    
    if (verticalAdvertsCard) {
        verticalAdvertsCard.style.display = 'block';
        // Update card title based on advert type
        const verticalTitle = verticalAdvertsCard.querySelector('.card-header h5');
        if (verticalTitle) {
            verticalTitle.textContent = config.advert_type === 'single' ? 'Adverts' : 'Vertical Adverts';
        }
    }
    
    if (horizontalAdvertsCard) {
        horizontalAdvertsCard.style.display = config.advert_type === 'vertical_horizontal' ? 'block' : 'none';
    }
}

// Authentication
function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        alert('Please enter both username and password');
        return;
    }
    
    credentials = btoa(username + ':' + password);
    
    // Hide login modal and show main content
    const loginModal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
    loginModal.hide();
    document.getElementById('mainContent').style.display = 'block';
}

// API call helper
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Authorization': 'Basic ' + credentials,
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${BACKEND_URL}/api${endpoint}`, options);
        
        if (response.status === 401) {
            alert('Authentication failed. Please refresh and login again.');
            location.reload();
            return null;
        }
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error Response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        alert('API call failed: ' + error.message);
        return null;
    }
}

// Fetch email data
async function fetchData() {
    const spinner = document.getElementById('fetchSpinner');
    const button = spinner.parentElement;
    
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        const requestData = {
            email_type: currentEmailType,
            num_news: parseInt(document.getElementById('numNews').value),
            num_business: parseInt(document.getElementById('numBusiness').value),
            num_sports: parseInt(document.getElementById('numSports').value),
            num_community: parseInt(document.getElementById('numCommunity').value),
            num_podcast: parseInt(document.getElementById('numPodcast').value),
            deaths_start: document.getElementById('deathsStart').value || '',
            deaths_end: document.getElementById('deathsEnd').value || ''
        };
        
        const response = await apiCall('/fetch-data', 'POST', requestData);
        
        if (response) {
            console.log('Received response from API:', response);
            console.log('Response news stories count:', response.news_stories?.length || 0);
            emailData = response;
            console.log('Updated emailData:', emailData);
            updateTables();
            updateFamilyNotices();
            updateWeather();
            updateJEPFields();  // Update JEP-specific fields if applicable
            updateJEPAdverts();  // Update JEP adverts if applicable
            updateAdvertTables(); // Update advert tables
            showAlert('Data fetched successfully!', 'success');
            console.log('About to call updatePreview...');
            updatePreview();
            attachPreviewUpdateListeners();
        }
    } finally {
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

// Update JEP-specific fields
function updateJEPFields() {
    if (currentEmailType === 'jep' && emailData.jep_cover) {
        const jepCoverField = document.getElementById('jepCover');
        const jepPublicationField = document.getElementById('jepPublication');
        
        if (jepCoverField) jepCoverField.value = emailData.jep_cover || '';
        if (jepPublicationField) jepPublicationField.value = emailData.publication || '';
    }
}

// Update JEP adverts (placeholder for now - JEP uses different advert structure)
function updateJEPAdverts() {
    // JEP adverts are handled differently - they're part of the single adverts array
    // This function is called during email type switching but doesn't need to do anything
    // until we implement full JEP advert management
}

// Process manual URLs
async function processManualUrls() {
    const urls = document.getElementById('manualUrls').value.trim();
    if (!urls) {
        alert('Please enter at least one URL');
        return;
    }
    
    const urlList = urls.split('\n').map(url => url.trim()).filter(url => url);
    const storyType = document.getElementById('storyType').value;
    
    const spinner = document.getElementById('urlSpinner');
    const button = spinner.parentElement;
    
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        const response = await apiCall('/scrape-urls', 'POST', { urls: urlList });
        
        if (response && response.length > 0) {
            // Add the scraped stories to the selected category
            emailData[storyType] = [...emailData[storyType], ...response];
            updateTables();
            updatePreview();
            document.getElementById('manualUrls').value = '';
            showAlert(`Added ${response.length} stories successfully!`, 'success');
        }
    } finally {
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

// Update story tables
function updateTables() {
    updateTable('newsTable', emailData.news_stories, 'news_stories');
    updateTable('businessTable', emailData.business_stories, 'business_stories');
    updateTable('sportsTable', emailData.sports_stories, 'sports_stories');
    updateTable('communityTable', emailData.community_stories, 'community_stories');
    updateTable('podcastTable', emailData.podcast_stories, 'podcast_stories');
}

function updateTable(tableId, stories, storyType) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = '';
    
    stories.forEach((story, index) => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>
                <input type="number" class="form-control form-control-sm order-input" 
                       value="${story.order}" 
                       onchange="updateStoryOrder('${storyType}', ${index}, this.value)">
            </td>
            <td>
                <div class="story-headline" title="${story.headline}">
                    ${story.headline}
                </div>
            </td>
            <td>${story.author}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editStory('${storyType}', ${index})">
                    Edit
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="removeStory('${storyType}', ${index})">
                    Remove
                </button>
            </td>
        `;
    });
}

// Story management functions
function updateStoryOrder(storyType, index, newOrder) {
    emailData[storyType][index].order = parseInt(newOrder);
    // Re-sort stories by order
    emailData[storyType].sort((a, b) => a.order - b.order);
    updateTable(getTableId(storyType), emailData[storyType], storyType);
    updatePreview();
}

function editStory(storyType, index) {
    const story = emailData[storyType][index];
    
    // Populate the edit modal
    document.getElementById('editOrder').value = story.order;
    document.getElementById('editHeadline').value = story.headline;
    document.getElementById('editText').value = story.text;
    document.getElementById('editAuthor').value = story.author;
    document.getElementById('editUrl').value = story.url;
    document.getElementById('editImageUrl').value = story.image_url;
    document.getElementById('editStoryType').value = storyType;
    document.getElementById('editStoryIndex').value = index;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('storyEditModal'));
    modal.show();
}

function saveStoryEdit() {
    const storyType = document.getElementById('editStoryType').value;
    const index = parseInt(document.getElementById('editStoryIndex').value);
    
    if (storyType === 'adverts') {
        // Handle JEP adverts
        emailData.adverts[index] = {
            order: parseInt(document.getElementById('editOrder').value),
            url: document.getElementById('editUrl').value,
            image_url: document.getElementById('editImageUrl').value
        };
        updateJEPAdverts();
        
        // Show all fields again for next use
        document.getElementById('editHeadline').closest('.mb-3').style.display = 'block';
        document.getElementById('editText').closest('.mb-3').style.display = 'block';
        document.getElementById('editAuthor').closest('.mb-3').style.display = 'block';
    } else {
        // Update the story with form values
        emailData[storyType][index] = {
            ...emailData[storyType][index],
            order: parseInt(document.getElementById('editOrder').value),
            headline: document.getElementById('editHeadline').value,
            text: document.getElementById('editText').value,
            author: document.getElementById('editAuthor').value,
            url: document.getElementById('editUrl').value,
            image_url: document.getElementById('editImageUrl').value
        };
        
        // Update the table
        updateTable(getTableId(storyType), emailData[storyType], storyType);
    }
    
    updatePreview();
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('storyEditModal'));
    modal.hide();
}

function removeStory(storyType, index) {
    if (confirm('Are you sure you want to remove this story?')) {
        emailData[storyType].splice(index, 1);
        updateTable(getTableId(storyType), emailData[storyType], storyType);
        updatePreview();
    }
}

function getTableId(storyType) {
    const mapping = {
        'news_stories': 'newsTable',
        'business_stories': 'businessTable',
        'sports_stories': 'sportsTable',
        'community_stories': 'communityTable',
        'podcast_stories': 'podcastTable'
    };
    return mapping[storyType];
}

// Update family notices display
function updateFamilyNotices() {
    const container = document.getElementById('familyNotices');
    
    if (emailData.family_notices && emailData.family_notices.length > 0) {
        container.innerHTML = emailData.family_notices.map((notice, index) => `
            <div class="family-notice">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6>${notice.name}</h6>
                        <p><strong>Funeral Director:</strong> ${notice.funeral_director}</p>
                        ${notice.additional_text ? `<p>${notice.additional_text}</p>` : ''}
                        <p><a href="${notice.url}" target="_blank" class="btn btn-sm btn-outline-primary">View Notice</a></p>
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" onclick="editFamilyNotice(${index})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeFamilyNotice(${index})">Remove</button>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="text-muted">No family notices found</p>';
    }
}

function editFamilyNotice(index) {
    if (index === undefined || index === null) {
        if (!emailData.family_notices || emailData.family_notices.length === 0) {
            showAlert('No family notices to edit. Add one first.', 'warning');
            return;
        }
        index = 0;
    }
    const notice = emailData.family_notices[index];
    
    document.getElementById('editNoticeName').value = notice.name;
    document.getElementById('editNoticeDirector').value = notice.funeral_director;
    document.getElementById('editNoticeText').value = notice.additional_text || '';
    document.getElementById('editNoticeUrl').value = notice.url;
    document.getElementById('editNoticeIndex').value = index;
    
    const modal = new bootstrap.Modal(document.getElementById('familyNoticeEditModal'));
    modal.show();
}

function saveFamilyNoticeEdit() {
    const index = parseInt(document.getElementById('editNoticeIndex').value);
    
    emailData.family_notices[index] = {
        name: document.getElementById('editNoticeName').value,
        funeral_director: document.getElementById('editNoticeDirector').value,
        additional_text: document.getElementById('editNoticeText').value,
        url: document.getElementById('editNoticeUrl').value
    };
    
    updateFamilyNotices();
    updatePreview();
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('familyNoticeEditModal'));
    modal.hide();
}

function addFamilyNotice() {
    // Add a blank notice
    emailData.family_notices.push({
        name: 'New Notice',
        funeral_director: '',
        additional_text: '',
        url: ''
    });
    
    updateFamilyNotices();
    // Immediately edit the new notice
    editFamilyNotice(emailData.family_notices.length - 1);
}

function removeFamilyNotice(index) {
    if (confirm('Are you sure you want to remove this family notice?')) {
        emailData.family_notices.splice(index, 1);
        updateFamilyNotices();
        updatePreview();
    }
}

// Update weather display
function updateWeather() {
    const container = document.getElementById('weather');
    
    if (emailData.weather && (emailData.weather.todays_weather || emailData.weather.tides || emailData.weather.date)) {
        const weather = emailData.weather;
        let weatherHtml = '<div class="weather-info">';
        
        if (weather.todays_weather) {
            weatherHtml += `<p><strong>Today's weather:</strong> ${weather.todays_weather}</p>`;
        }
        if (weather.tides) {
            weatherHtml += `<p><strong>Tides:</strong> ${weather.tides}</p>`;
        }
        if (weather.date) {
            weatherHtml += `<p><strong>Date:</strong> ${weather.date}</p>`;
        }
        
        weatherHtml += '</div>';
        container.innerHTML = weatherHtml;
    } else {
        container.innerHTML = '<p class="text-muted">No weather data available</p>';
    }
}

function editWeather() {
    const weather = emailData.weather || {};
    document.getElementById('editWeatherToday').value = weather.todays_weather || '';
    document.getElementById('editWeatherTides').value = weather.tides || '';
    document.getElementById('editWeatherDate').value = weather.date || '';
    
    const modal = new bootstrap.Modal(document.getElementById('weatherEditModal'));
    modal.show();
}

function saveWeatherEdit() {
    emailData.weather = {
        todays_weather: document.getElementById('editWeatherToday').value,
        tides: document.getElementById('editWeatherTides').value,
        date: document.getElementById('editWeatherDate').value
    };
    updateWeather();
    updatePreview();
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('weatherEditModal'));
    modal.hide();
}

// JEP Adverts management
function updateJEPAdverts() {
    const config = getCurrentConfig();
    if (config.advert_type !== 'single') return;
    
    const container = document.getElementById('jepAdverts');
    
    if (emailData.adverts && emailData.adverts.length > 0) {
        container.innerHTML = emailData.adverts.map((advert, index) => `
            <div class="jep-advert-item mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>Order:</strong> ${advert.order || index + 1} | 
                        <a href="${advert.url}" target="_blank">View Advert</a>
                        ${advert.image_url ? ` | <a href="${advert.image_url}" target="_blank">Image</a>` : ''}
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" onclick="editJEPAdvert(${index})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeJEPAdvert(${index})">Remove</button>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="text-muted">No adverts loaded</p>';
    }
}

function addJEPAdvert() {
    if (!emailData.adverts) emailData.adverts = [];
    emailData.adverts.push({
        order: emailData.adverts.length + 1,
        url: '',
        image_url: ''
    });
    updateJEPAdverts();
    // Immediately edit the new advert
    editJEPAdvert(emailData.adverts.length - 1);
}

function editJEPAdvert(index) {
    // We can reuse the story edit modal for adverts with some adjustments
    const advert = emailData.adverts[index];
    
    document.getElementById('editOrder').value = advert.order || index + 1;
    document.getElementById('editHeadline').value = 'Advert';
    document.getElementById('editText').value = '';
    document.getElementById('editAuthor').value = '';
    document.getElementById('editUrl').value = advert.url;
    document.getElementById('editImageUrl').value = advert.image_url;
    document.getElementById('editStoryType').value = 'adverts';
    document.getElementById('editStoryIndex').value = index;
    
    // Hide irrelevant fields for adverts
    document.getElementById('editHeadline').closest('.mb-3').style.display = 'none';
    document.getElementById('editText').closest('.mb-3').style.display = 'none';
    document.getElementById('editAuthor').closest('.mb-3').style.display = 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('storyEditModal'));
    modal.show();
}

function removeJEPAdvert(index) {
    if (confirm('Are you sure you want to remove this advert?')) {
        emailData.adverts.splice(index, 1);
        updateJEPAdverts();
        updatePreview();
    }
}

// Live preview functionality
function updatePreview() {
    refreshPreview();
}

async function refreshPreview() {
    console.log('refreshPreview called');
    const spinner = document.getElementById('previewSpinner');
    const preview = document.getElementById('livePreview');
    
    console.log('Spinner element:', spinner);
    console.log('Preview element:', preview);
    
    if (!spinner) {
        console.error('Preview spinner not found');
        return;
    }
    
    if (!preview) {
        console.error('Live preview iframe not found');
        return;
    }
    
    spinner.classList.remove('d-none');
    
    try {
        console.log('Current emailData:', emailData);
        console.log('EmailData keys:', emailData ? Object.keys(emailData) : 'emailData is null/undefined');
        console.log('News stories count:', emailData?.news_stories?.length || 0);
        
        // Check if emailData exists and has data
        if (!emailData || Object.keys(emailData).length === 0) {
            console.warn('No email data available for preview');
            preview.srcdoc = '<p style="padding: 20px; text-align: center; color: #666;">No data loaded. Please fetch data first.</p>';
            return;
        }
        
        // Check if there are any news stories before rendering
        if (!emailData.news_stories || emailData.news_stories.length === 0) {
            console.warn('No news stories available for preview - news_stories:', emailData.news_stories);
            preview.srcdoc = '<p style="padding: 20px; text-align: center; color: #666;">No news stories available. Please fetch data first.</p>';
            return;
        }
        
        // Collect top image data
        const topImage = {
            title: document.getElementById('topImageTitle').value,
            url: document.getElementById('topImageUrl').value,
            author: document.getElementById('topImageAuthor').value,
            link: document.getElementById('topImageLink').value
        };
        
        console.log('Top image data:', topImage);
        
        const fullEmailData = {
            ...emailData,
            email_type: currentEmailType,
            top_image: topImage,
            vertical_adverts: emailData.vertical_adverts || [],
            horizontal_adverts: emailData.horizontal_adverts || []
        };
        
        // Add JEP-specific fields if applicable
        if (currentEmailType === 'jep') {
            fullEmailData.jep_cover = document.getElementById('jepCover')?.value || '';
            fullEmailData.publication = document.getElementById('jepPublication')?.value || '';
            fullEmailData.date = new Date().toLocaleDateString('en-US', {
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric'
            });
        }
        
        console.log('Full email data for API call:', fullEmailData);
        
        const response = await apiCall('/generate-email', 'POST', fullEmailData);
        console.log('API response:', response);
        
        if (response && response.html) {
            console.log('Setting iframe content via srcdoc. HTML length:', response.html.length);
            const preview = document.getElementById('livePreview');
            
            // Clear any existing src attribute to avoid conflicts
            preview.removeAttribute('src');
            
            // Set the HTML content directly
            preview.srcdoc = response.html;
            console.log('Preview updated successfully');
        } else {
            console.error('No HTML in response:', response);
            preview.srcdoc = '<p style="padding: 20px; text-align: center; color: #f00;">Error: No HTML content received from server</p>';
        }
    } catch (error) {
        console.error('Preview update failed:', error);
        preview.srcdoc = '<p style="padding: 20px; text-align: center; color: #f00;">Error: ' + error.message + '</p>';
    } finally {
        spinner.classList.add('d-none');
    }
}

// Generate final email (separate from live preview)
async function generateFinalEmail() {
    const spinner = document.getElementById('finalSpinner');
    const button = spinner.parentElement;
    
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        // Check if there are any news stories before generating
        if (!emailData || !emailData.news_stories || emailData.news_stories.length === 0) {
            showAlert('No news stories available. Please fetch data first.', 'warning');
            return;
        }
        
        // Collect top image data
        const topImage = {
            title: document.getElementById('topImageTitle').value,
            url: document.getElementById('topImageUrl').value,
            author: document.getElementById('topImageAuthor').value,
            link: document.getElementById('topImageLink').value
        };
        
        const fullEmailData = {
            ...emailData,
            email_type: currentEmailType,
            top_image: topImage,
            vertical_adverts: emailData.vertical_adverts || [],
            horizontal_adverts: emailData.horizontal_adverts || []
        };
        
        // Add JEP-specific fields if applicable
        if (currentEmailType === 'jep') {
            fullEmailData.jep_cover = document.getElementById('jepCover')?.value || '';
            fullEmailData.publication = document.getElementById('jepPublication')?.value || '';
            fullEmailData.date = new Date().toLocaleDateString('en-US', {
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric'
            });
        }
        
        const response = await apiCall('/generate-email', 'POST', fullEmailData);
        
        if (response && response.html) {
            // Show email preview in modal
            const preview = document.getElementById('emailPreview');
            preview.srcdoc = response.html;
            
            const modal = new bootstrap.Modal(document.getElementById('emailPreviewModal'));
            modal.show();
        }
    } finally {
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

// Download email HTML
function downloadEmail() {
    const iframe = document.getElementById('emailPreview');
    const html = iframe.contentDocument.documentElement.outerHTML;
    
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `be-email-${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Adverts Management
function updateAdvertTables() {
    const config = getCurrentConfig();
    
    if (config.advert_type === 'vertical_horizontal') {
        updateAdvertTable('verticalAdvertsTable', emailData.vertical_adverts || [], 'vertical');
        updateAdvertTable('horizontalAdvertsTable', emailData.horizontal_adverts || [], 'horizontal');
    } else if (config.advert_type === 'single') {
        updateAdvertTable('verticalAdvertsTable', emailData.vertical_adverts || [], 'vertical');
        // Hide horizontal table for single advert types
        const horizontalTable = document.getElementById('horizontalAdvertsTable');
        if (horizontalTable) {
            horizontalTable.closest('.advert-section').style.display = 'none';
        }
    }
}

function updateAdvertTable(tableId, adverts, advertType) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    adverts.forEach((advert, index) => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>
                <input type="number" class="form-control form-control-sm order-input" 
                       value="${advert.order || index + 1}" 
                       onchange="updateAdvertOrder('${advertType}', ${index}, this.value)">
            </td>
            <td>
                <div title="${advert.url}">
                    ${advert.url ? `<a href="${advert.url}" target="_blank">${advert.url.substring(0, 40)}...</a>` : 'No URL'}
                </div>
            </td>
            <td>
                <div title="${advert.image_url}">
                    ${advert.image_url ? `<a href="${advert.image_url}" target="_blank">View Image</a>` : 'No Image'}
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editAdvert('${advertType}', ${index})">
                    Edit
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="removeAdvert('${advertType}', ${index})">
                    Remove
                </button>
            </td>
        `;
    });
}

function addAdvert(advertType) {
    const newAdvert = {
        order: (emailData[`${advertType}_adverts`]?.length || 0) + 1,
        url: '',
        image_url: ''
    };
    
    if (currentEmailType === 'jep' && advertType === 'vertical') {
        // For JEP, store in adverts array
        if (!emailData.adverts) emailData.adverts = [];
        emailData.adverts.push(newAdvert);
        emailData.vertical_adverts = emailData.adverts; // Mirror for display
    } else {
        // For BE/GE, store in appropriate array
        if (!emailData[`${advertType}_adverts`]) emailData[`${advertType}_adverts`] = [];
        emailData[`${advertType}_adverts`].push(newAdvert);
    }
    
    updateAdvertTables();
    
    // Immediately edit the new advert
    const index = (emailData[`${advertType}_adverts`]?.length || 1) - 1;
    editAdvert(advertType, index);
}

function editAdvert(advertType, index) {
    const adverts = emailData[`${advertType}_adverts`] || [];
    const advert = adverts[index];
    
    if (!advert) return;
    
    document.getElementById('editAdvertOrder').value = advert.order || index + 1;
    document.getElementById('editAdvertUrl').value = advert.url || '';
    document.getElementById('editAdvertImageUrl').value = advert.image_url || '';
    document.getElementById('editAdvertType').value = advertType;
    document.getElementById('editAdvertIndex').value = index;
    
    const modal = new bootstrap.Modal(document.getElementById('advertEditModal'));
    modal.show();
}

function saveAdvertEdit() {
    const advertType = document.getElementById('editAdvertType').value;
    const index = parseInt(document.getElementById('editAdvertIndex').value);
    
    const updatedAdvert = {
        order: parseInt(document.getElementById('editAdvertOrder').value),
        url: document.getElementById('editAdvertUrl').value,
        image_url: document.getElementById('editAdvertImageUrl').value
    };
    
    if (currentEmailType === 'jep' && advertType === 'vertical') {
        // Update JEP adverts
        emailData.adverts[index] = updatedAdvert;
        emailData.vertical_adverts = emailData.adverts; // Mirror for display
    } else {
        // Update BE/GE adverts
        emailData[`${advertType}_adverts`][index] = updatedAdvert;
    }
    
    updateAdvertTables();
    updatePreview();
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('advertEditModal'));
    modal.hide();
}

function removeAdvert(advertType, index) {
    if (confirm('Are you sure you want to remove this advert?')) {
        if (currentEmailType === 'jep' && advertType === 'vertical') {
            emailData.adverts.splice(index, 1);
            emailData.vertical_adverts = emailData.adverts; // Mirror for display
        } else {
            emailData[`${advertType}_adverts`].splice(index, 1);
        }
        
        updateAdvertTables();
        updatePreview();
    }
}

function updateAdvertOrder(advertType, index, newOrder) {
    const order = parseInt(newOrder);
    
    if (currentEmailType === 'jep' && advertType === 'vertical') {
        emailData.adverts[index].order = order;
        emailData.adverts.sort((a, b) => (a.order || 0) - (b.order || 0));
        emailData.vertical_adverts = emailData.adverts; // Mirror for display
    } else {
        emailData[`${advertType}_adverts`][index].order = order;
        emailData[`${advertType}_adverts`].sort((a, b) => (a.order || 0) - (b.order || 0));
    }
    
    updateAdvertTables();
    updatePreview();
}

async function saveAdverts() {
    // Prevent any form submission
    event.preventDefault();
    
    console.log('=== SAVE ADVERTS STARTED ===');
    
    const spinner = document.getElementById('saveAdvertsSpinner');
    const button = spinner.parentElement;
    
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        const requestData = {
            email_type: currentEmailType,
            vertical_adverts: emailData.vertical_adverts || [],
            horizontal_adverts: emailData.horizontal_adverts || []
        };
        
        console.log('Saving adverts with data:', requestData);
        console.log('Current email type:', currentEmailType);
        console.log('Credentials available:', !!credentials);
        
        if (!credentials) {
            showAlert('Not logged in. Please refresh the page and log in again.', 'warning');
            return;
        }
        
        const response = await apiCall('/save-adverts', 'POST', requestData);
        
        if (response) {
            console.log('=== ADVERTS SAVED SUCCESSFULLY ===');
            // Temporarily disabled: showAlert('Adverts saved successfully!', 'success');
        } else {
            console.log('=== NO RESPONSE RECEIVED ===');
        }
        console.log('=== SAVE ADVERTS COMPLETED ===');
    } catch (error) {
        console.error('=== ERROR IN SAVE ADVERTS ===', error);
        // Temporarily disabled: showAlert('Failed to save adverts: ' + error.message, 'danger');
    } finally {
        console.log('=== SAVE ADVERTS FINALLY BLOCK ===');
        spinner.classList.add('d-none');
        button.disabled = false;
    }
    
    console.log('=== SAVE ADVERTS FUNCTION ENDED ===');
    return false; // Prevent any default behavior
}

async function loadAdverts() {
    const spinner = document.getElementById('loadAdvertsSpinner');
    const button = spinner.parentElement;
    
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        console.log('Loading adverts for email type:', currentEmailType);
        const response = await apiCall(`/load-adverts/${currentEmailType}`, 'GET');
        
        if (response) {
            console.log('Loaded adverts response:', response);
            emailData.vertical_adverts = response.vertical_adverts || [];
            emailData.horizontal_adverts = response.horizontal_adverts || [];
            
            // For single advert types, sync adverts with vertical_adverts
            const config = getCurrentConfig();
            if (config.advert_type === 'single') {
                emailData.adverts = emailData.vertical_adverts;
            }
            
            updateAdvertTables();
            updatePreview();
            showAlert('Adverts loaded successfully!', 'success');
        }
    } finally {
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container-fluid').insertBefore(alertDiv, document.querySelector('.row'));
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}
