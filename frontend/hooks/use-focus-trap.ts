import { useEffect, useRef } from 'react';

/**
 * useFocusTrap - a small hook to manage focus within a modal/dialog.
 * Usage example:
 *   const { modalRef, initialFocusRef, onKeyDown } = useFocusTrap(() => setShowModal(false));
 *   <div ref={modalRef} onKeyDown={onKeyDown} role="dialog" aria-modal="true" ...>
 *     <input ref={initialFocusRef} ... />
 *   </div>
 */
export function useFocusTrap(onClose: () => void) {
  const modalRef = useRef<HTMLDivElement>(null);
  const initialFocusRef = useRef<HTMLElement>(null);
  const previouslyFocused = useRef<Element | null>(null);

  useEffect(() => {
    // Save element that had focus before opening modal
    previouslyFocused.current = document.activeElement;
    // Focus the initial element when modal mounts
    if (initialFocusRef.current) {
      (initialFocusRef.current as HTMLElement).focus();
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (focusable.length === 0) return;
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to previously focused element
      if (previouslyFocused.current instanceof HTMLElement) {
        previouslyFocused.current.focus();
      }
    };
  }, [onClose]);

  // Return refs for modal container and initial focus element; onKeyDown can be attached to modal container
  return {
    modalRef,
    initialFocusRef,
    onKeyDown: (e: React.KeyboardEvent) => {},
  };
}
