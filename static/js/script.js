// Form validation
$(document).ready(function() {
    // Mobile number validation
    $('input[type="tel"]').on('input', function() {
        let value = $(this).val();
        value = value.replace(/\D/g, '');
        if (value.length > 10) {
            value = value.slice(0, 10);
        }
        $(this).val(value);
    });
    
    // Aadhaar number validation
    $('#aadhaar').on('input', function() {
        let value = $(this).val();
        value = value.replace(/\D/g, '');
        if (value.length > 12) {
            value = value.slice(0, 12);
        }
        $(this).val(value);
    });
    
    // Age validation
    $('#age').on('input', function() {
        let value = $(this).val();
        value = value.replace(/\D/g, '');
        if (value.length > 2) {
            value = value.slice(0, 2);
        }
        $(this).val(value);
    });
    
    // Form submission with loading state
    $('form').on('submit', function() {
        let btn = $(this).find('button[type="submit"]');
        btn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...');
        btn.prop('disabled', true);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
});

// Email validation function
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// File upload preview
function previewFile(input, previewId) {
    const file = input.files[0];
    const preview = document.getElementById(previewId);
    
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            if (file.type.startsWith('image/')) {
                preview.innerHTML = `<img src="${e.target.result}" class="img-thumbnail" style="max-height: 200px;">`;
            } else {
                preview.innerHTML = `<p class="text-success"><i class="fas fa-check-circle"></i> File selected: ${file.name}</p>`;
            }
        }
        reader.readAsDataURL(file);
    }
}

// Print function
function printDiv(divId) {
    let printContents = document.getElementById(divId).innerHTML;
    let originalContents = document.body.innerHTML;
    
    document.body.innerHTML = printContents;
    window.print();
    document.body.innerHTML = originalContents;
    location.reload();
}

// Search functionality
function searchTable(inputId, tableId) {
    let input = document.getElementById(inputId);
    let filter = input.value.toUpperCase();
    let table = document.getElementById(tableId);
    let tr = table.getElementsByTagName("tr");
    
    for (let i = 1; i < tr.length; i++) {
        let tdArray = tr[i].getElementsByTagName("td");
        let found = false;
        
        for (let j = 0; j < tdArray.length; j++) {
            let td = tdArray[j];
            if (td) {
                let txtValue = td.textContent || td.innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        if (found) {
            tr[i].style.display = "";
        } else {
            tr[i].style.display = "none";
        }
    }
}

// Confirmation dialog
function confirmAction(message, url) {
    if (confirm(message)) {
        window.location.href = url;
    }
}

// Date formatter
function formatDate(dateString) {
    let date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Number formatter (Indian currency)
function formatCurrency(amount) {
    return '₹' + amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}