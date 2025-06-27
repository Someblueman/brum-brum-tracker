/**
 * Tests for logbook UI functionality
 */

// Mock logbook UI
class MockLogbookUI {
    constructor() {
        this.container = {
            innerHTML: '',
            children: []
        };
        this.entries = [];
        this.sortOrder = 'desc';
        this.filterType = 'all';
    }
    
    async loadEntries() {
        // Simulate API call
        return new Promise((resolve) => {
            setTimeout(() => {
                this.entries = [
                    {
                        id: 1,
                        spotted_at: '2024-01-01T10:00:00',
                        aircraft_type: 'Boeing 737',
                        image_url: 'https://example.com/b737.jpg'
                    },
                    {
                        id: 2,
                        spotted_at: '2024-01-01T11:00:00',
                        aircraft_type: 'Airbus A320',
                        image_url: 'https://example.com/a320.jpg'
                    },
                    {
                        id: 3,
                        spotted_at: '2024-01-01T12:00:00',
                        aircraft_type: 'Boeing 777',
                        image_url: null
                    }
                ];
                this.renderEntries();
                resolve(this.entries);
            }, 10);
        });
    }
    
    renderEntries() {
        const filtered = this.filterEntries();
        const sorted = this.sortEntries(filtered);
        
        this.container.children = sorted.map(entry => ({
            className: 'logbook-entry',
            dataset: { id: entry.id },
            innerHTML: this.createEntryHTML(entry)
        }));
        
        this.container.innerHTML = this.container.children
            .map(child => `<div class="${child.className}" data-id="${child.dataset.id}">${child.innerHTML}</div>`)
            .join('');
    }
    
    createEntryHTML(entry) {
        const date = new Date(entry.spotted_at);
        const imageHtml = entry.image_url 
            ? `<img src="${entry.image_url}" alt="${entry.aircraft_type}">` 
            : '<div class="no-image">No Image</div>';
            
        return `
            <div class="entry-image">${imageHtml}</div>
            <div class="entry-details">
                <h3>${entry.aircraft_type}</h3>
                <p>${date.toLocaleString()}</p>
            </div>
        `;
    }
    
    filterEntries() {
        if (this.filterType === 'all') {
            return this.entries;
        }
        
        return this.entries.filter(entry => {
            const type = entry.aircraft_type.toLowerCase();
            if (this.filterType === 'boeing') return type.includes('boeing');
            if (this.filterType === 'airbus') return type.includes('airbus');
            return true;
        });
    }
    
    sortEntries(entries) {
        return [...entries].sort((a, b) => {
            const dateA = new Date(a.spotted_at);
            const dateB = new Date(b.spotted_at);
            return this.sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
        });
    }
    
    setSortOrder(order) {
        this.sortOrder = order;
        this.renderEntries();
    }
    
    setFilter(filter) {
        this.filterType = filter;
        this.renderEntries();
    }
    
    getEntryCount() {
        return this.entries.length;
    }
    
    getVisibleEntryCount() {
        return this.filterEntries().length;
    }
    
    deleteEntry(id) {
        this.entries = this.entries.filter(entry => entry.id !== id);
        this.renderEntries();
    }
    
    addEntry(entry) {
        const newEntry = {
            ...entry,
            id: Math.max(...this.entries.map(e => e.id), 0) + 1
        };
        this.entries.push(newEntry);
        this.renderEntries();
        return newEntry;
    }
}

describe('Logbook UI Tests', async (it) => {
    
    it('should load and display entries', async () => {
        const logbook = new MockLogbookUI();
        const entries = await logbook.loadEntries();
        
        assert.equal(entries.length, 3);
        assert.equal(logbook.getEntryCount(), 3);
        assert.equal(logbook.container.children.length, 3);
    });
    
    it('should sort entries by date', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        // Default sort is descending (newest first)
        const firstEntry = logbook.container.children[0];
        assert.equal(firstEntry.dataset.id, 3); // Latest entry
        
        // Change to ascending
        logbook.setSortOrder('asc');
        const firstEntryAsc = logbook.container.children[0];
        assert.equal(firstEntryAsc.dataset.id, 1); // Earliest entry
    });
    
    it('should filter entries by aircraft type', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        // Filter Boeing aircraft
        logbook.setFilter('boeing');
        assert.equal(logbook.getVisibleEntryCount(), 2);
        
        // Filter Airbus aircraft
        logbook.setFilter('airbus');
        assert.equal(logbook.getVisibleEntryCount(), 1);
        
        // Show all
        logbook.setFilter('all');
        assert.equal(logbook.getVisibleEntryCount(), 3);
    });
    
    it('should render entries with proper HTML structure', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        const html = logbook.container.innerHTML;
        
        // Check for required elements
        assert.isTrue(html.includes('Boeing 737'));
        assert.isTrue(html.includes('Airbus A320'));
        assert.isTrue(html.includes('Boeing 777'));
        assert.isTrue(html.includes('logbook-entry'));
        assert.isTrue(html.includes('entry-image'));
        assert.isTrue(html.includes('entry-details'));
    });
    
    it('should handle entries without images', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        const html = logbook.container.innerHTML;
        assert.isTrue(html.includes('No Image')); // Entry 3 has no image
    });
    
    it('should delete entries', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        assert.equal(logbook.getEntryCount(), 3);
        
        logbook.deleteEntry(2);
        assert.equal(logbook.getEntryCount(), 2);
        
        // Verify the deleted entry is not in the rendered output
        const html = logbook.container.innerHTML;
        assert.isFalse(html.includes('Airbus A320'));
    });
    
    it('should add new entries', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        const newEntry = {
            spotted_at: '2024-01-01T13:00:00',
            aircraft_type: 'Embraer E195',
            image_url: 'https://example.com/e195.jpg'
        };
        
        const added = logbook.addEntry(newEntry);
        
        assert.equal(logbook.getEntryCount(), 4);
        assert.equal(added.id, 4);
        assert.equal(added.aircraft_type, 'Embraer E195');
        
        // Verify new entry appears in rendered output
        const html = logbook.container.innerHTML;
        assert.isTrue(html.includes('Embraer E195'));
    });
    
    it('should maintain filter after adding entries', async () => {
        const logbook = new MockLogbookUI();
        await logbook.loadEntries();
        
        // Set filter to Boeing
        logbook.setFilter('boeing');
        assert.equal(logbook.getVisibleEntryCount(), 2);
        
        // Add a new Airbus
        logbook.addEntry({
            spotted_at: '2024-01-01T14:00:00',
            aircraft_type: 'Airbus A350',
            image_url: null
        });
        
        // Boeing filter should still be active
        assert.equal(logbook.getVisibleEntryCount(), 2); // Still only Boeing aircraft visible
        
        // Switch to show all
        logbook.setFilter('all');
        assert.equal(logbook.getVisibleEntryCount(), 4); // All 4 entries visible
    });
});