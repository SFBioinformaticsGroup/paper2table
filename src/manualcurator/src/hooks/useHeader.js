import { useEffect, useState } from 'react';

export default function useHeader(headerRef) {
  const [headerHeight, setHeaderHeight] = useState(0);
  const [isPinned, setIsPinned] = useState(false);

  useEffect(() => {
    function updateHeight() {
      const h = headerRef.current ? headerRef.current.offsetHeight : 0;
      setHeaderHeight(h);
    }
    function updatePin() {
      const pinned = headerRef.current ? window.scrollY > headerRef.current.offsetTop : false;
      setIsPinned(pinned);
    }
    updateHeight();
    updatePin();
    window.addEventListener('resize', updateHeight);
    window.addEventListener('scroll', updatePin, { passive: true });
    return () => {
      window.removeEventListener('resize', updateHeight);
      window.removeEventListener('scroll', updatePin, { passive: true });
    };
  }, [headerRef]);

  return { headerHeight, isPinned };
}
