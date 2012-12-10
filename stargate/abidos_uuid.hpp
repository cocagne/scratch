#ifndef ABIDOS_UUID_H
#define ABIDOS_UUID_H

#include <string.h>
#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_generators.hpp>

#include "abidos_common.hpp"

namespace abidos
{
   
class UUID : public sg::UUID
{
  public:
   boost::uuids::uuid  uid;
            
   void setUniqueValue()
   {
      boost::uuids::uuid tmp = boost::uuids::random_generator()();
      memcpy(&uid, &tmp, sizeof(uid));
   }
      
   void zero()
   {
      memset( uid.data, 0, sizeof(uid.data) );
   }
      
   bool isValid() const
   {
      for( int i=0; i < sizeof(uid.data); i++ )
         if ( uid.data[i] != 0 )
            return true;
      return false;
   }
      
   UUID & operator=( int value ) // used by constructors
   {
      assert( value == 0 );
      zero();
      return *this;
   }

   virtual bool operator<( const sg::UUID  * rhs ) const
   {
      return uid < static_cast<const UUID*>(rhs)->uid;
   }
      
   virtual bool operator==( const sg::UUID * rhs ) const
   {
      return uid == static_cast<const UUID*>(rhs)->uid;
   }
};
   
inline std::size_t hash_value( UUID const & u )
{
   return boost::uuids::hash_value( u.uid );
}
   
inline std::size_t hash_value( UUID * const & pu )
{
   return boost::uuids::hash_value( pu->uid );
}


struct puuid_equal :
      std::binary_function< const UUID *, const UUID *, bool >
{
   bool operator()( const UUID * const & px, const UUID * const & py ) const
   {
      return px->uid == py->uid;
   }
};

// For use in STL maps
struct puuid_less
{
   bool operator()( const UUID * x, const UUID * y ) const
   {
      return x->uid < y->uid;
   }
};
   

} // end namespace abidos


#endif

