import React, { useState } from 'react';
import { Container } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearchPlus, faSearchMinus, faRedo, faUndo, faSyncAlt } from '@fortawesome/free-solid-svg-icons';


const ImageViewer = ({ src, setDirection }) => {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  // Zoom in
  const zoomIn = () => setScale(prevScale => prevScale * 1.2);

  // Zoom out
  const zoomOut = () => setScale(prevScale => Math.max(0.1, prevScale / 1.2));

  // Reset to default
  const reset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setDirection('north');
  };



  return (
    <Container className="text-center mt-4">
      <div className="image-container">

          <div>
            <img
              src={src}
              alt="Viewer"
              style={{
                transform: `scale(${scale})`,
                transition: 'transform 0.2s',
                maxWidth: '100%',
                height: 'auto',
                userSelect: 'none', // Prevent text selection
                WebkitUserDrag: 'none', // Disable dragging in WebKit browsers
              }}
              className="draggable-image"
            />
          </div>

        <div className="compass">
          <div className="direction north" onClick={() => setDirection('north')}>
            N
          </div>
          <div className="direction east" onClick={() => setDirection('east')}>
            E
          </div>
          <div className="direction south" onClick={() => setDirection('south')}>
            S
          </div>
          <div className="direction west" onClick={() => setDirection('west')}>
            W
          </div>
          <div className="direction nadir" onClick={() => setDirection('nadir')}>
            T
          </div>
        </div>
      </div>
      <div className="mt-3">
        <FontAwesomeIcon icon={faSearchPlus} className="icon mx-2" onClick={zoomIn} title="Zoom In" />
        <FontAwesomeIcon icon={faSearchMinus} className="icon mx-2" onClick={zoomOut} title="Zoom Out" />
        <FontAwesomeIcon icon={faSyncAlt} className="icon mx-2" onClick={reset} title="Reset" />
      </div>
    </Container>
  );
};

export default ImageViewer;
