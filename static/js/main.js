// Modal functions
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

// Phone input management
function addPhoneInput() {
    const container = document.getElementById('phone-inputs');
    const row = document.createElement('div');
    row.className = 'phone-row';
    row.innerHTML = `
        <input type="text" name="phones[]" class="form-control" placeholder="Telefon belgisi">
        <button type="button" class="btn-remove-phone" onclick="removePhoneInput(this)">✕</button>
    `;
    container.appendChild(row);
}

function removePhoneInput(btn) {
    btn.parentElement.remove();
}

// Subscriber selection for orders
function selectSubscriber(select) {
    const option = select.options[select.selectedIndex];
    if (option.dataset.type) {
        document.getElementById('selected-client-type').textContent =
            option.dataset.type === 'legal' ? 'Ýuridik şahs' : 'Fiziki şahs';
        updateOrderPrices(option.dataset.type);
    }
}

function updateOrderPrices(clientType) {
    const prices = window.currentPrices || {};
    const suffix = clientType === 'legal' ? 'legal' : 'individual';

    document.getElementById('price-new').textContent = prices[`new_${suffix}`] || '-';
    document.getElementById('price-exchange').textContent = prices[`exchange_${suffix}`] || '-';
    document.getElementById('price-water').textContent = prices[`water_${suffix}`] || '-';
}

// Edit subscriber modal
function editSubscriber(id, name, type, phones) {
    document.getElementById('edit-subscriber-id').value = id;
    document.getElementById('edit-full-name').value = name;
    document.getElementById('edit-client-type').value = type;

    const container = document.getElementById('edit-phone-inputs');
    container.innerHTML = '';

    const phonesArr = phones ? phones.split(',') : [];
    phonesArr.forEach(phone => {
        const row = document.createElement('div');
        row.className = 'phone-row';
        row.innerHTML = `
            <input type="text" name="phones[]" class="form-control" value="${phone.trim()}" placeholder="Telefon belgisi">
            <button type="button" class="btn-remove-phone" onclick="removePhoneInput(this)">✕</button>
        `;
        container.appendChild(row);
    });

    if (phonesArr.length === 0) {
        addEditPhoneInput();
    }

    document.getElementById('edit-subscriber-form').action = `/subscribers/${id}/edit`;
    openModal('edit-subscriber-modal');
}

function addEditPhoneInput() {
    const container = document.getElementById('edit-phone-inputs');
    const row = document.createElement('div');
    row.className = 'phone-row';
    row.innerHTML = `
        <input type="text" name="phones[]" class="form-control" placeholder="Telefon belgisi">
        <button type="button" class="btn-remove-phone" onclick="removePhoneInput(this)">✕</button>
    `;
    container.appendChild(row);
}

// Confirm delete
function confirmDelete(form, message) {
    if (confirm(message || 'Öçürmek isleýärsiňizmi?')) {
        form.submit();
    }
    return false;
}

// Edit user modal
function editUser(id, username, role) {
    document.getElementById('edit-user-id').value = id;
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-role').value = role;
    document.getElementById('edit-user-form').action = `/admin/users/${id}/edit`;
    openModal('edit-user-modal');
}

// Payment modal
function openPaymentModal(subscriberId, name, debt) {
    document.getElementById('payment-subscriber-id').value = subscriberId;
    document.getElementById('payment-subscriber-name').textContent = name;
    document.getElementById('payment-current-debt').textContent = debt + ' TMT';
    openModal('payment-modal');
}
