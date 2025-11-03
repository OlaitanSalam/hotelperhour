/* ------------------------------------------------------------------ */
/*  favorites.js – Complete, Fixed, Ready to Use                      */
/* ------------------------------------------------------------------ */

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

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = 9999;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

/* ------------------------------------------------------------------ */
/*  TOGGLE FAVORITE – Instant UI Updates (Guest + Logged-in)          */
/* ------------------------------------------------------------------ */
function toggleFavorite(slug, button) {
    if (window.isHotelOwner) {
        showToast('This feature is only available to guests. Switch to a customer account to use it.', 'warning');
        return;
    }

    // ——— LOGGED-IN CUSTOMER ———
    if (window.isLoggedIn && window.isCustomer) {
        fetch(`/customers/favorite/${slug}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(r => r.json())
        .then(data => {
            const icon = button.querySelector('i');
            if (data.added) {
                button.classList.add('favorited');
                icon.classList.replace('far', 'fas');
                button.dataset.tooltip = 'Remove from favorites';
                showToast('Saved to favorites!', 'success');
            } else {
                button.classList.remove('favorited');
                icon.classList.replace('fas', 'far');
                button.dataset.tooltip = 'Save to favorites';
                showToast('Removed from favorites', 'info');

               const isFavoritesPage =
                   window.location.pathname.includes('/customer_favorites') ||
                   window.location.pathname.includes('/guest_favorites');

               if (isFavoritesPage && card) {
                   card.remove();
                   updateEmptyState();
               }

            }
        })
        .catch(() => showToast('Something went wrong. Please try again shortly.', 'danger'));
        return;
    }

    // ——— GUEST (localStorage) ———
    let wishlist = JSON.parse(localStorage.getItem('wishlist') || '[]');
    const idx = wishlist.indexOf(slug);

    if (idx > -1) { // REMOVE
        wishlist.splice(idx, 1);
        button.classList.remove('favorited');
        button.querySelector('i').classList.replace('fas', 'far');
        button.dataset.tooltip = 'Save to favorites';
        showToast('Removed from your favorites.', 'info');

        const isFavoritesPage =
                   window.location.pathname.includes('/customer_favorites') ||
                   window.location.pathname.includes('/guest_favorites');

               if (isFavoritesPage && card) {
                   card.remove();
                   updateEmptyState();
               }
    } else { // ADD
        wishlist.push(slug);
        button.classList.add('favorited');
        button.querySelector('i').classList.replace('far', 'fas');
        button.dataset.tooltip = 'Remove from favorites';
        showToast('Added to your favorites! Sign in to keep them saved across devices.', 'success');
    }

    localStorage.setItem('wishlist', JSON.stringify(wishlist));
    updateEmptyState();
}

/* ------------------------------------------------------------------ */
/*  RESTORE HEARTS ON PAGE LOAD (Guest only)                          */
/* ------------------------------------------------------------------ */
function restoreLocalFavorites() {
    if (window.isLoggedIn && window.isCustomer) return;

    const wishlist = JSON.parse(localStorage.getItem('wishlist') || '[]');
    if (!wishlist.length) return;

    document.querySelectorAll('.favorite-btn').forEach(btn => {
        const match = btn.getAttribute('onclick')?.match(/'([^']+)'/);
        if (match && wishlist.includes(match[1])) {
            btn.classList.add('favorited');
            const i = btn.querySelector('i');
            if (i.classList.contains('far')) {
                i.classList.replace('far', 'fas');
            }
            btn.dataset.tooltip = 'Remove from favorites';
        }
    });
}

/* ------------------------------------------------------------------ */
/*  SYNC LOCAL → SERVER ON LOGIN                                      */
/* ------------------------------------------------------------------ */
function syncOnLogin() {
    if (!window.isLoggedIn || !window.isCustomer) return;

    const wishlist = JSON.parse(localStorage.getItem('wishlist') || '[]');
    if (!wishlist.length) return;

    fetch('/customers/sync_favorites/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(wishlist.map(s => ['slugs[]', s]))
    })
    .then(r => r.json())
    .then(data => {
        if (data.added) {
            showToast(`Your saved favorites have been synced to your account.`, 'success');
        }
        localStorage.removeItem('wishlist');
    })
    .catch(() => showToast('We couldn’t sync your favorites right now. Please try again later.', 'danger'));
}

/* ------------------------------------------------------------------ */
/*  UPDATE EMPTY STATE – Show/Hide "No hotels" instantly              */
/* ------------------------------------------------------------------ */
/* ------------------------------------------------------------------ */
/*  UPDATE EMPTY STATE – Works for BOTH Guest & Logged-in             */
/* ------------------------------------------------------------------ */
function updateEmptyState() {
    const container = document.querySelector('#guestList, .row.row-cols-1');
    const empty = document.getElementById('emptyState');
    if (!container || !empty) return;

    const hasCards = container.children.length > 0;
    const isGuest = !(window.isLoggedIn && window.isCustomer);

    if (isGuest) {
        const wishlist = JSON.parse(localStorage.getItem('wishlist') || '[]');
        if (wishlist.length === 0 || !hasCards) {
            container.style.display = 'none';
            empty.style.display = 'block';
        } else {
            container.style.display = '';
            empty.style.display = 'none';
        }
    } else {
        // Logged-in: show empty if no cards
        if (!hasCards) {
            container.style.display = 'none';
            empty.style.display = 'block';
        } else {
            container.style.display = '';
            empty.style.display = 'none';
        }
    }
}

/* ------------------------------------------------------------------ */
/*  INIT – Run on every page load                                     */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
    restoreLocalFavorites();
    syncOnLogin();
    updateEmptyState(); // ← Critical for instant empty state
});