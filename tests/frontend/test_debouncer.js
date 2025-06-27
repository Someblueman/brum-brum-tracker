/**
 * Tests for the debouncer module
 */

import { debounce, throttle, createMessageBatcher, createSearchDebouncer } from '../../frontend/js/modules/debouncer.js';

describe('Debouncer Module', () => {
    describe('debounce', () => {
        it('should delay function execution', (done) => {
            let callCount = 0;
            const fn = () => callCount++;
            const debounced = debounce(fn, 50);
            
            debounced();
            debounced();
            debounced();
            
            expect(callCount).toBe(0);
            
            setTimeout(() => {
                expect(callCount).toBe(1);
                done();
            }, 100);
        });
        
        it('should support leading edge execution', (done) => {
            let callCount = 0;
            const fn = () => callCount++;
            const debounced = debounce(fn, 50, { leading: true });
            
            debounced();
            expect(callCount).toBe(1);
            
            debounced();
            expect(callCount).toBe(1);
            
            setTimeout(() => {
                expect(callCount).toBe(1);
                done();
            }, 100);
        });
        
        it('should support maxWait option', (done) => {
            let callCount = 0;
            const fn = () => callCount++;
            const debounced = debounce(fn, 100, { maxWait: 150 });
            
            const interval = setInterval(() => debounced(), 50);
            
            setTimeout(() => {
                clearInterval(interval);
                expect(callCount).toBeGreaterThan(0);
                done();
            }, 300);
        });
        
        it('should support cancel method', () => {
            let callCount = 0;
            const fn = () => callCount++;
            const debounced = debounce(fn, 50);
            
            debounced();
            debounced.cancel();
            
            setTimeout(() => {
                expect(callCount).toBe(0);
            }, 100);
        });
        
        it('should support flush method', () => {
            let callCount = 0;
            const fn = () => callCount++;
            const debounced = debounce(fn, 50);
            
            debounced();
            debounced.flush();
            
            expect(callCount).toBe(1);
        });
    });
    
    describe('throttle', () => {
        it('should limit function execution rate', (done) => {
            let callCount = 0;
            const fn = () => callCount++;
            const throttled = throttle(fn, 50);
            
            // Call multiple times rapidly
            for (let i = 0; i < 10; i++) {
                throttled();
            }
            
            // Should be called immediately (leading edge)
            expect(callCount).toBe(1);
            
            setTimeout(() => {
                // Should be called at most twice (leading + trailing)
                expect(callCount).toBeLessThanOrEqual(2);
                done();
            }, 100);
        });
        
        it('should support trailing option', (done) => {
            let callCount = 0;
            const fn = () => callCount++;
            const throttled = throttle(fn, 50, { leading: false, trailing: true });
            
            throttled();
            throttled();
            
            expect(callCount).toBe(0);
            
            setTimeout(() => {
                expect(callCount).toBe(1);
                done();
            }, 100);
        });
    });
    
    describe('createMessageBatcher', () => {
        it('should batch multiple messages', (done) => {
            const sentMessages = [];
            const sendFunc = (msg) => sentMessages.push(msg);
            const batcher = createMessageBatcher(sendFunc, 50);
            
            batcher.send({ type: 'test1' });
            batcher.send({ type: 'test2' });
            batcher.send({ type: 'test3' });
            
            expect(sentMessages.length).toBe(0);
            
            setTimeout(() => {
                expect(sentMessages.length).toBe(1);
                expect(sentMessages[0].type).toBe('batch');
                expect(sentMessages[0].messages.length).toBe(3);
                done();
            }, 100);
        });
        
        it('should send single message when only one', (done) => {
            const sentMessages = [];
            const sendFunc = (msg) => sentMessages.push(msg);
            const batcher = createMessageBatcher(sendFunc, 50);
            
            batcher.send({ type: 'test' });
            
            setTimeout(() => {
                expect(sentMessages.length).toBe(1);
                expect(sentMessages[0].type).toBe('test');
                done();
            }, 100);
        });
        
        it('should respect maxBatchSize', () => {
            const sentMessages = [];
            const sendFunc = (msg) => sentMessages.push(msg);
            const batcher = createMessageBatcher(sendFunc, 50, 3);
            
            // Send 4 messages
            batcher.send({ type: 'test1' });
            batcher.send({ type: 'test2' });
            batcher.send({ type: 'test3' });
            batcher.send({ type: 'test4' }); // This should trigger immediate send
            
            expect(sentMessages.length).toBe(1);
            expect(sentMessages[0].messages.length).toBe(3);
        });
        
        it('should support flush method', () => {
            const sentMessages = [];
            const sendFunc = (msg) => sentMessages.push(msg);
            const batcher = createMessageBatcher(sendFunc, 50);
            
            batcher.send({ type: 'test1' });
            batcher.send({ type: 'test2' });
            batcher.flush();
            
            expect(sentMessages.length).toBe(1);
            expect(sentMessages[0].messages.length).toBe(2);
        });
        
        it('should support cancel method', (done) => {
            const sentMessages = [];
            const sendFunc = (msg) => sentMessages.push(msg);
            const batcher = createMessageBatcher(sendFunc, 50);
            
            batcher.send({ type: 'test' });
            batcher.cancel();
            
            setTimeout(() => {
                expect(sentMessages.length).toBe(0);
                done();
            }, 100);
        });
    });
    
    describe('createSearchDebouncer', () => {
        it('should debounce search queries', (done) => {
            let searchCount = 0;
            const searchFunc = async (query) => {
                searchCount++;
                return `Results for ${query}`;
            };
            const debouncedSearch = createSearchDebouncer(searchFunc, 50);
            
            debouncedSearch('test1');
            debouncedSearch('test2');
            debouncedSearch('test3');
            
            expect(searchCount).toBe(0);
            
            setTimeout(() => {
                expect(searchCount).toBe(1);
                done();
            }, 100);
        });
        
        it('should cancel previous searches', async () => {
            let activeSearches = 0;
            const searchFunc = async (query) => {
                activeSearches++;
                await new Promise(resolve => setTimeout(resolve, 100));
                activeSearches--;
                return `Results for ${query}`;
            };
            const debouncedSearch = createSearchDebouncer(searchFunc, 10);
            
            // Start multiple searches
            const search1 = debouncedSearch('test1');
            await new Promise(resolve => setTimeout(resolve, 20));
            const search2 = debouncedSearch('test2');
            
            // Wait for searches to complete
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Only the last search should have completed
            expect(activeSearches).toBe(0);
        });
    });
});