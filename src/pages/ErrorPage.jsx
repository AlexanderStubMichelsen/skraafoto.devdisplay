import React from 'react';
import { Link } from 'react-router-dom';
import "../App.css";

const ErrorPage = () => {
  return (
    <div className="error-page">
      <h1>404</h1>
      <h2>Page Not Found</h2>
      <p>Sorry, the page you're looking for doesn't exist.</p>
      <Link to="/" className="home-link">
        Go Back to Home
      </Link>
    </div>
  );
};

export default ErrorPage;
