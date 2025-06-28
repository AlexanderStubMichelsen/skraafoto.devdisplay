import AsyncSelect, { useAsync } from 'react-select/async';
import { addressToCoords, addressAutocomplete } from "../util/addressSearch";

function AddressSearch({ setCoordinates=null, setAddress=null}) { // TODO: a setState to update the coords that are beeing looked at

  const onChange = async (event) => {
    if(setCoordinates)    
      setCoordinates(await addressToCoords(event.value))
    if(setAddress)
      setAddress(event.value)
  }
  const promiseOptions = async (event) => {
    if (event === "") return;
    return await addressAutocomplete(event);
  };
  
      

  return (
    <>
      <div>
        <AsyncSelect 
          cacheOptions 
          defaultOptions 
          loadOptions={promiseOptions} 
          onChange={onChange}
          placeholder="Search.."  // Set your custom placeholder here
          isClearable
        />
      </div>
    </>
  );
}

export default AddressSearch;