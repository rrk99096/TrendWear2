document.addEventListener('DOMContentLoaded', function() {
    console.log("TrendWear JS Loaded");

    // --- 1. FILTER FUNCTIONALITY ---
    const filterButtons = document.querySelectorAll('.toggle-btn');
    const products = document.querySelectorAll('.product-card');

    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove 'active' class from all buttons
            filterButtons.forEach(b => b.classList.remove('active'));
            // Add 'active' to the clicked button
            btn.classList.add('active');

            const filterValue = btn.getAttribute('data-filter');

            products.forEach(card => {
                // Read the data tags we added in HTML
                const isRent = card.getAttribute('data-rent') === 'true';
                const isSale = card.getAttribute('data-sale') === 'true';

                // Logic: Show or Hide based on button
                if (filterValue === 'all') {
                    card.style.display = 'block';
                } else if (filterValue === 'rent') {
                    // Show if it's for rent
                    card.style.display = isRent ? 'block' : 'none';
                } else if (filterValue === 'sale') {
                    // Show if it's for sale
                    card.style.display = isSale ? 'block' : 'none';
                }
            });
        });
    });

    // --- 2. ADD TO CART / RENT ANIMATION ---
    const actionButtons = document.querySelectorAll('.btn-overlay');
    const cartCount = document.querySelector('.cart-count');
    let count = 0;

    actionButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Increase number
            count++;
            cartCount.innerText = count;

            // Visual Feedback (Change button text briefly)
            const originalText = this.innerText;
            this.innerText = "Added!";
            this.style.backgroundColor = "#27ae60"; // Green color
            
            setTimeout(() => {
                this.innerText = originalText;
                this.style.backgroundColor = ""; // Reset color
            }, 1000);
        });
    });

    // --- 3. NAVBAR SCROLL (Keep existing code) ---
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }

        
    });
});

const searchIcon = document.querySelector('.fa-search'); // Ensure your icon has this class
    const searchOverlay = document.querySelector('.search-overlay');
    const closeSearch = document.querySelector('.close-search');

    if(searchIcon) {
        searchIcon.addEventListener('click', (e) => {
            e.preventDefault();
            searchOverlay.classList.add('active');
        });
    }

    if(closeSearch) {
        closeSearch.addEventListener('click', () => {
            searchOverlay.classList.remove('active');
        });
    }

    /* =========================================
   PRODUCT PAGE LOGIC
   ========================================= */

// 1. STATE MANAGEMENT
let selectedVariantId = initialVariantId; // Value comes from HTML script tag
const priceDisplay = document.querySelector('.product-price');

// 2. IMAGE GALLERY
function changeImage(thumb, src) {
    // Update Main Image
    document.getElementById('mainImage').src = src;
    
    // Update Active Class on Thumbnails
    document.querySelectorAll('.thumb-img').forEach(t => t.classList.remove('active'));
    thumb.classList.add('active');
}

// 3. SIZE SELECTION & PRICE UPDATE
function selectSize(btn, variantId, variantPrice) {
    // A. Visual: Highlight Button
    document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // B. Logic: Update ID
    selectedVariantId = variantId;

    // C. Price: Update Display
    if (variantPrice && variantPrice !== 'None') {
        priceDisplay.innerText = "$" + variantPrice;
    } else {
        priceDisplay.innerText = "$" + BASE_PRICE;
    }
}

// 4. ADD TO CART FUNCTION
function addToCart(actionType) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Get Date Inputs (if they exist)
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const startDate = startDateInput ? startDateInput.value : null;
    const endDate = endDateInput ? endDateInput.value : null;

    // --- VALIDATION ---
    
    // Check Login
    if (IS_LOGGED_IN === 'false') {
        // Redirect to login page and come back here after
        window.location.href = LOGIN_URL + "?next=" + window.location.pathname;
        return;
    }

    // Check Size (If sizes exist, one must be selected)
    // We check if the initial ID was set. If yes, that means variants exist.
    if (initialVariantId !== null && !selectedVariantId) {
        alert("Please select a size.");
        return;
    }

    // Check Dates (Only for rental)
    if (actionType === 'rent') {
        if (!startDate || !endDate) {
            alert("Please select Start and End dates for rental.");
            return;
        }
    }

    // --- SEND REQUEST ---
    const btn = event.target; // Get button to show "Adding..."
    const originalText = btn.innerText;
    btn.innerText = "Adding...";
    btn.disabled = true;

    fetch(CART_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            product_id: PRODUCT_ID,
            variant_id: selectedVariantId,
            action_type: actionType,
            start_date: startDate,
            end_date: endDate
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Update Cart Count in Navbar
            const badge = document.querySelector('.cart-count');
            if(badge) badge.innerText = data.cart_count;
            
            alert(data.message);
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Something went wrong. Check console.");
    })
    .finally(() => {
        // Reset Button
        btn.innerText = originalText;
        btn.disabled = false;
    });
}document.addEventListener('DOMContentLoaded', function() {
    
    // 1. NAVBAR SCROLL EFFECT
    const navbar = document.getElementById('navbar');
    if(navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) { navbar.classList.add('scrolled'); } 
            else { navbar.classList.remove('scrolled'); }
        });
    }

    // 2. SIDEBAR FILTER (Home Page)
    const sidebar = document.getElementById('filterSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleBtn = document.getElementById('filterToggle');
    const closeBtn = document.getElementById('closeFilter');

    if(toggleBtn && sidebar) {
        function openSidebar() { sidebar.classList.add('active'); overlay.classList.add('active'); }
        function closeSidebar() { sidebar.classList.remove('active'); overlay.classList.remove('active'); }
        toggleBtn.addEventListener('click', openSidebar);
        if(closeBtn) closeBtn.addEventListener('click', closeSidebar);
        if(overlay) overlay.addEventListener('click', closeSidebar);
    }

    // 3. SEARCH OVERLAY
    const searchIcon = document.querySelector('.fa-search'); 
    const searchOverlay = document.getElementById('search-overlay');
    const closeSearch = document.querySelector('.close-search');

    if(searchIcon && searchOverlay) {
        searchIcon.addEventListener('click', (e) => { e.preventDefault(); searchOverlay.classList.add('active'); });
        if(closeSearch) closeSearch.addEventListener('click', () => searchOverlay.classList.remove('active'));
    }

    // 4. INVENTORY TOGGLE (Inventory Page)
    window.toggleRow = function(id) {
        var panel = document.getElementById("panel-" + id);
        var arrow = document.getElementById("arrow-" + id);
        var parent = panel.previousElementSibling;
        if (panel.style.display === "table-row") {
            panel.style.display = "none";
            arrow.style.transform = "rotate(0deg)";
            parent.classList.remove("active");
        } else {
            panel.style.display = "table-row";
            arrow.style.transform = "rotate(90deg)";
            parent.classList.add("active");
        }
    }

    // 5. PRODUCT DETAIL PAGE LOGIC
    // Note: 'allVariants' variable must be defined in the HTML before this runs
    if (typeof allVariants !== 'undefined') {
        renderSizeButtons(); 
        setupDateRestrictions();
        
        const startInput = document.getElementById('start_date');
        const endInput = document.getElementById('end_date');
        if(startInput) startInput.addEventListener('change', calculateTotal);
        if(endInput) endInput.addEventListener('change', calculateTotal);
    }
});

// --- HELPER FUNCTIONS FOR PRODUCT PAGE ---
let currentRentPrice = 0;

function changeImage(thumb, src) {
    const mainImg = document.getElementById('mainImage');
    if (mainImg) mainImg.src = src;
    document.querySelectorAll('.thumb-img').forEach(t => t.classList.remove('active'));
    thumb.classList.add('active');
}

function renderSizeButtons() {
    const container = document.getElementById('size-container');
    if(!container) return;
    container.innerHTML = '';
    const sizes = [...new Set(allVariants.map(v => v.size))];
    sizes.forEach(size => {
        const btn = document.createElement('button');
        btn.type = "button"; btn.className = 'option-btn'; btn.innerText = size;
        btn.onclick = () => selectSize(size, btn);
        container.appendChild(btn);
    });
    if(sizes.length > 0) selectSize(sizes[0], container.firstChild);
}

function selectSize(size, btnElement) {
    document.querySelectorAll('#size-container .option-btn').forEach(b => b.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    renderColorButtons(size);
}

function renderColorButtons(size) {
    const container = document.getElementById('color-container');
    if(!container) return;
    container.innerHTML = '';
    const compatibleVariants = allVariants.filter(v => v.size === size);
    
    compatibleVariants.forEach(v => {
        const btn = document.createElement('button');
        btn.type = "button"; btn.className = 'option-btn'; btn.innerText = v.color;
        if (v.stock < 1) {
            btn.classList.add('disabled'); btn.disabled = true;
        } else {
            btn.onclick = () => selectColor(v, btn);
        }
        container.appendChild(btn);
    });

    const available = compatibleVariants.filter(v => v.stock > 0);
    if(available.length > 0) {
        const buttons = Array.from(container.children);
        const targetBtn = buttons.find(b => b.innerText === available[0].color);
        if(targetBtn) selectColor(available[0], targetBtn);
    }
}

function selectColor(variant, btnElement) {
    document.getElementById('selected-variant-id').value = variant.id;
    currentRentPrice = variant.rent;
    document.querySelectorAll('#color-container .option-btn').forEach(b => b.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    const saleDisplay = document.getElementById('display-sale-price');
    const rentDisplay = document.getElementById('display-rent-price');
    if(saleDisplay) saleDisplay.innerText = variant.sale;
    if(rentDisplay) rentDisplay.innerText = variant.rent;
    calculateTotal(); 
}

function calculateTotal() {
    const startDateVal = document.getElementById('start_date');
    const endDateVal = document.getElementById('end_date');
    const totalBox = document.getElementById('rental-total-box');
    
    if (startDateVal && endDateVal && startDateVal.value && endDateVal.value && currentRentPrice) {
        const start = new Date(startDateVal.value);
        const end = new Date(endDateVal.value);
        const diffTime = end - start;
        let diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
        if (diffDays === 0) diffDays = 1; 

        if (diffDays > 0) {
            const totalCost = diffDays * parseFloat(currentRentPrice);
            totalBox.style.display = 'block';
            document.getElementById('display-total-price').innerText = "$" + totalCost.toFixed(2);
            document.getElementById('rental-days-count').innerText = "(" + diffDays + " days)";
        } else {
            totalBox.style.display = 'none';
        }
    }
}

function setupDateRestrictions() {
    var startInput = document.getElementById('start_date');
    var endInput = document.getElementById('end_date');
    if (!startInput || !endInput) return;
    var today = new Date();
    today.setDate(today.getDate() + 2); 
    var minDate = today.toISOString().split('T')[0];
    startInput.setAttribute('min', minDate);
    endInput.setAttribute('min', minDate);
    startInput.addEventListener('change', function() {
        endInput.setAttribute('min', this.value);
    });
}

function validateForm() {
    const variantId = document.getElementById('selected-variant-id').value;
    if (!variantId) { alert("Please select a valid Size and Color."); return false; }
    return true; 
}

// --- OTP LOGIC ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function sendOTP(url) {
    const email = document.querySelector('input[name="email"]').value;
    const btn = document.getElementById('otpBtn');
    const msg = document.getElementById('otpMessage');
    const otpField = document.getElementById('otpField');
    const csrftoken = getCookie('csrftoken');

    if(!email) { alert("Enter email first"); return; }
    btn.innerText = "Sending..."; btn.disabled = true;

    fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ email: email })
    })
    .then(r => r.json())
    .then(d => {
        msg.style.display = 'block';
        if(d.status === 'success') {
            msg.innerText = "Code sent!"; msg.style.color = 'green';
            otpField.style.display = 'block'; btn.innerText = "Sent";
        } else {
            msg.innerText = d.message; msg.style.color = 'red'; btn.disabled = false; btn.innerText = "Try Again";
        }
    });
}