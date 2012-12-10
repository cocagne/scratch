#ifndef ABIDOS_ERROR_H
#define ABIDOS_ERROR_H

namespace abidos
{

//--------------------------------------------------------------------------
// AbidosError
// 
// Base class for all Abidos exceptions
//
// Implementation defined in abidos_common.cpp
//
class AbidosError : public std::exception
{
  protected:
   std::string err_msg;
      
  public:
   AbidosError( const std::string & msg );
      
   ~AbidosError() throw ();
      
   virtual const char * what() const throw();
};


} // end namespace abidos


#endif
