/* =========================================
   PRODUCT LOGIC (Matches new HTML)
   ========================================= */

let currentVariantId = (typeof initialVariantId !== 'undefined') ? initialVariantId : null;

// Initialize prices
let activeBtn = document.querySelector('.size-btn.active');
let currentSalePrice = activeBtn ? activeBtn.dataset.sale : '0.00';
let currentRentPrice = activeBtn ? activeBtn.dataset.rent : '0.00';

function changeImage(thumb, src) {
    const mainImg = document.getElementById('mainImage');
    if (mainImg) mainImg.src = src;
    document.querySelectorAll('.thumb-img').forEach(t => t.classList.remove('active'));
    thumb.classList.add('active');
}

function selectSize(btn) {
    // 1. Highlight
    document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // 2. Update Data
    currentVariantId = btn.dataset.id;
    currentSalePrice = btn.dataset.sale;
    currentRentPrice = btn.dataset.rent;

    // 3. Update Text
    const saleDisplay = document.getElementById('display-sale-price');
    const rentDisplay = document.getElementById('display-rent-price');

    if(saleDisplay) saleDisplay.innerText = currentSalePrice;
    if(rentDisplay) rentDisplay.innerText = currentRentPrice;

    // 4. Recalculate
    calculateTotal();
}

function calculateTotal() {
    const startDateVal = document.getElementById('startDate').value;
    const endDateVal = document.getElementById('endDate').value;
    const totalBox = document.getElementById('rental-total-box');
    const totalDisplay = document.getElementById('display-total-price');
    const daysDisplay = document.getElementById('rental-days-count');

    if (startDateVal && endDateVal) {
        const start = new Date(startDateVal);
        const end = new Date(endDateVal);
        const diffTime = Math.abs(end - start);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 

        if (diffDays > 0) {
            const totalCost = diffDays * parseFloat(currentRentPrice);
            totalBox.style.display = 'block';
            totalDisplay.innerText = "$" + totalCost.toFixed(2);
            daysDisplay.innerText = "(" + diffDays + " days)";
        } else {
            if(totalBox) totalBox.style.display = 'none';
        }
    }
}

function addToCart(actionType) {
    // ... (Keep existing Add to Cart logic) ...
    // Just ensure you include the fetch call as provided in previous steps
    
    // Quick boilerplate if you lost it:
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const startDate = document.getElementById('startDate') ? document.getElementById('startDate').value : null;
    const endDate = document.getElementById('endDate') ? document.getElementById('endDate').value : null;
    
    if (IS_LOGGED_IN === 'false') { window.location.href = LOGIN_URL + "?next=" + window.location.pathname; return; }
    if (!currentVariantId) { alert("Please select a size."); return; }
    if (actionType === 'rent' && (!startDate || !endDate)) { alert("Select dates."); return; }

    const btn = event.target;
    btn.innerText = "Processing...";
    btn.disabled = true;

    fetch(CART_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({
            product_id: PRODUCT_ID, variant_id: currentVariantId, action_type: actionType, start_date: startDate, end_date: endDate
        })
    })
    .then(r => r.json())
    .then(d => { 
        if(d.status === 'success') { document.querySelector('.cart-count').innerText = d.cart_count; alert(d.message); }
        else { alert("Error: " + d.message); }
    })
    .finally(() => { btn.innerText = (actionType === 'rent' ? "RENT IT" : "BUY NOW"); btn.disabled = false; });
}