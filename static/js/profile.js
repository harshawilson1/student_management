    const editBtn = document.getElementById('editBtn');
    const saveBtn = document.getElementById('saveBtn');
    const form = document.getElementById('profileForm');

    editBtn.addEventListener('click', () => {
        // Make all inputs editable
        form.querySelectorAll('input').forEach(input => input.removeAttribute('readonly'));

        // Show save button, hide edit button
        saveBtn.style.display = 'inline-block';
        editBtn.style.display = 'none';
    });