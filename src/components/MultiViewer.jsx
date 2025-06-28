import React, { useState } from 'react';
import { Container } from 'react-bootstrap';

const MultiViewer = ({ src, onClick }) => {
  const [scale, setScale] = useState(1);


  return (
    <Container className="text-center" onClick={onClick}> {/* Add onClick here */}
      <div className="image-container-multi">

          <div>
            <img
              src={src}
              alt="Viewer"
              style={{
                transform: `scale(${scale})`,
                transition: 'transform 0.2s',
                maxWidth: '100%',
                height: 'auto',
                userSelect: 'none',
                WebkitUserDrag: 'none',
              }}
              className="draggable-image"
            />
          </div>
      </div>
    </Container>
  );
};

export default MultiViewer;